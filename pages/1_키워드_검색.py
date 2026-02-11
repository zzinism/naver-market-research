import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.naver_api import search_products, NAVER_CLIENT_ID, features_to_str
from core.models import Product
from core.demo_data import DEMO_PRODUCTS_DESK, DEMO_ANALYSIS_DESK

st.set_page_config(page_title="키워드 검색", page_icon="🔍", layout="wide")
st.title("키워드 검색")

# 데모 모드 확인
demo_mode = not NAVER_CLIENT_ID
if demo_mode:
    st.warning("네이버 API 키가 설정되지 않았습니다. **데모 모드**로 실행됩니다.")

# 세션 상태 초기화
if "search_results" not in st.session_state:
    st.session_state.search_results = {}
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {}
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "feature_edits" not in st.session_state:
    st.session_state.feature_edits = {}

# URL 파라미터에서 키워드 복원
params_keyword = st.query_params.get("q", "")
params_sort = st.query_params.get("sort", "sim")

# 검색 입력
col_input, col_sort, col_btn = st.columns([3, 1, 1])

sort_options = ["sim", "date", "asc", "dsc"]

with col_input:
    keyword = st.text_input("검색 키워드", value=params_keyword, placeholder="예: 사무용 책상, 게이밍 의자")

with col_sort:
    sort_option = st.selectbox(
        "정렬",
        options=sort_options,
        index=sort_options.index(params_sort) if params_sort in sort_options else 0,
        format_func=lambda x: {
            "sim": "관련도순",
            "date": "날짜순",
            "asc": "가격 낮은순",
            "dsc": "가격 높은순",
        }[x],
    )

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    search_clicked = st.button("검색", type="primary", use_container_width=True)

# 새로고침 시 자동 재검색: URL에 키워드가 있지만 세션에 결과가 없는 경우
auto_search = bool(
    keyword
    and keyword not in st.session_state.search_results
    and not search_clicked
)

# 검색 실행
if (search_clicked or auto_search) and keyword:
    if demo_mode:
        products = DEMO_PRODUCTS_DESK
        st.session_state.search_results[keyword] = products
        from dataclasses import replace
        st.session_state.analysis_results[keyword] = replace(DEMO_ANALYSIS_DESK, keyword=keyword)
        st.session_state.search_history.append(
            {
                "keyword": keyword,
                "count": len(products),
                "time": datetime.now().strftime("%H:%M"),
            }
        )
        st.success(f"[데모] {len(products)}개 상품 데이터를 로드했습니다.")
    else:
        with st.spinner(f"'{keyword}' 검색 중..."):
            try:
                products = search_products(keyword, display=50, sort=sort_option)
                st.session_state.search_results[keyword] = products
                st.session_state.search_history.append(
                    {
                        "keyword": keyword,
                        "count": len(products),
                        "time": datetime.now().strftime("%H:%M"),
                    }
                )
                st.success(f"{len(products)}개 상품을 수집했습니다.")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"검색 실패: {e}")

    # URL 파라미터에 키워드 저장 (새로고침 시 복원용)
    st.query_params["q"] = keyword
    st.query_params["sort"] = sort_option

# 결과 표시
if keyword and keyword in st.session_state.search_results:
    products = st.session_state.search_results[keyword]

    if not products:
        st.warning("검색 결과가 없습니다.")
        st.stop()

    # KPI 카드
    prices = [p.lprice for p in products if p.lprice > 0]
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("상품 수", f"{len(products)}건")
    c2.metric("최저가", f"{min(prices):,}원" if prices else "-")
    c3.metric("최고가", f"{max(prices):,}원" if prices else "-")
    c4.metric("평균가", f"{int(sum(prices) / len(prices)):,}원" if prices else "-")

    # 가격 분포 차트 (더블클릭 시 가격비교 페이지 열기)
    st.subheader("가격 분포")
    st.caption("막대를 더블클릭하면 가격비교 페이지가 열립니다.")

    price_products = [p for p in products if p.lprice > 0]
    df_scatter = pd.DataFrame([
        {
            "상품명": p.title,
            "가격(원)": p.lprice,
            "브랜드": p.brand or "(브랜드 없음)",
            "주요 특징": features_to_str(p.title),
            "product_id": p.product_id,
        }
        for p in price_products
    ])
    df_scatter = df_scatter.sort_values("가격(원)").reset_index(drop=True)

    fig = px.bar(
        df_scatter,
        x=df_scatter.index,
        y="가격(원)",
        color="브랜드",
        text="브랜드",
        custom_data=["product_id", "상품명", "주요 특징"],
        labels={"x": "상품 (가격순)", "가격(원)": "가격 (원)"},
        color_discrete_sequence=px.colors.qualitative.Plotly,
    )
    fig.update_traces(
        textposition="outside",
        textfont_size=11,
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "가격: %{y:,}원<br>"
            "주요 특징: %{customdata[2]}"
            "<extra>%{fullData.name}</extra>"
        ),
    )
    fig.update_layout(
        xaxis=dict(showticklabels=False, title=None),
        yaxis=dict(title="가격 (원)"),
        bargap=0.05,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig_json = fig.to_json()
    chart_html = f"""
    <div id="priceChart" style="width:100%;height:500px;"></div>
    <script id="figData" type="application/json">{fig_json}</script>
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
    <script>
    var figParsed = JSON.parse(document.getElementById('figData').textContent);
    figParsed.layout.autosize = true;
    Plotly.newPlot('priceChart', figParsed.data, figParsed.layout, {{responsive: true}});

    var lastClickTime = 0;
    var lastPointIdx = -1;
    document.getElementById('priceChart').on('plotly_click', function(data) {{
        var now = Date.now();
        var point = data.points[0];
        var idx = point.pointIndex;
        if (now - lastClickTime < 400 && lastPointIdx === idx) {{
            var pid = point.customdata ? point.customdata[0] : null;
            if (pid) {{
                window.open('https://search.shopping.naver.com/catalog/' + pid, '_blank');
            }}
            lastClickTime = 0;
            lastPointIdx = -1;
        }} else {{
            lastClickTime = now;
            lastPointIdx = idx;
        }}
    }});
    </script>
    """
    components.html(chart_html, height=520)

    # 브랜드 분포 (상위 10개)
    brands = {}
    for p in products:
        b = p.brand or "(브랜드 없음)"
        brands[b] = brands.get(b, 0) + 1
    top_brands = sorted(brands.items(), key=lambda x: -x[1])[:10]

    col_brand, col_category = st.columns(2)

    with col_brand:
        st.subheader("브랜드 분포 (상위 10)")
        df_brand = pd.DataFrame(top_brands, columns=["브랜드", "상품수"])
        fig_brand = px.bar(df_brand, x="브랜드", y="상품수")
        st.plotly_chart(fig_brand, use_container_width=True)

    with col_category:
        st.subheader("브랜드 점유율")
        df_brand_pie = pd.DataFrame(top_brands, columns=["브랜드", "상품수"])
        fig_brand_pie = px.pie(df_brand_pie, names="브랜드", values="상품수")
        st.plotly_chart(fig_brand_pie, use_container_width=True)

    # 상품 테이블
    st.subheader("상품 목록")
    saved_edits = st.session_state.feature_edits.get(keyword, {})
    rank_to_pid = {}
    table_data = []
    for i, p in enumerate(products, 1):
        rank_to_pid[i] = p.product_id
        catalog_url = f"https://search.shopping.naver.com/catalog/{p.product_id}"
        table_data.append(
            {
                "순위": i,
                "이미지": p.image,
                "상품명": p.title,
                "특징(정리)": saved_edits.get(p.product_id, ""),
                "가격(원)": p.lprice if p.lprice else 0,
                "브랜드": p.brand or "-",
                "판매처": p.mall_name,
                "주요 특징 (상품명 추출)": features_to_str(p.title),
                "카테고리": f"{p.category1} > {p.category2}".rstrip(" > "),
                "가격비교": catalog_url,
                "스토어": p.link,
            }
        )

    df = pd.DataFrame(table_data)

    # 필터링
    with st.expander("필터", expanded=False):
        fc1, fc2, fc3 = st.columns(3)

        with fc1:
            brand_options = sorted(df["브랜드"].unique())
            selected_brands = st.multiselect("브랜드", brand_options, key="filter_brand")

        with fc2:
            mall_options = sorted(df["판매처"].unique())
            selected_malls = st.multiselect("판매처", mall_options, key="filter_mall")

        with fc3:
            cat_options = sorted(df["카테고리"].unique())
            selected_cats = st.multiselect("카테고리", cat_options, key="filter_cat")

        price_min = int(df["가격(원)"].min())
        price_max = int(df["가격(원)"].max())
        if price_min < price_max:
            price_range = st.slider(
                "가격 범위 (원)",
                min_value=price_min,
                max_value=price_max,
                value=(price_min, price_max),
                step=max(1, (price_max - price_min) // 100),
                format="%d원",
                key="filter_price",
            )
        else:
            price_range = (price_min, price_max)

        name_query = st.text_input("상품명 검색", key="filter_name", placeholder="상품명에 포함된 키워드")

    # 필터 적용
    filtered = df.copy()
    if selected_brands:
        filtered = filtered[filtered["브랜드"].isin(selected_brands)]
    if selected_malls:
        filtered = filtered[filtered["판매처"].isin(selected_malls)]
    if selected_cats:
        filtered = filtered[filtered["카테고리"].isin(selected_cats)]
    filtered = filtered[
        (filtered["가격(원)"] >= price_range[0]) & (filtered["가격(원)"] <= price_range[1])
    ]
    if name_query:
        filtered = filtered[filtered["상품명"].str.contains(name_query, case=False, na=False)]

    # 필터 결과 표시
    if len(filtered) < len(df):
        st.caption(f"전체 {len(df)}건 중 {len(filtered)}건 표시")

    # 편집 가능한 테이블 (특징(정리) 열만 편집 가능)
    disabled_cols = [col for col in filtered.columns if col != "특징(정리)"]
    edited_df = st.data_editor(
        filtered,
        use_container_width=True,
        hide_index=True,
        disabled=disabled_cols,
        column_config={
            "이미지": st.column_config.ImageColumn("이미지", width="small"),
            "가격(원)": st.column_config.NumberColumn("가격(원)", format="%d원"),
            "가격비교": st.column_config.LinkColumn("가격비교", display_text="가격비교"),
            "스토어": st.column_config.LinkColumn("스토어", display_text="스토어"),
            "특징(정리)": st.column_config.TextColumn(
                "특징(정리)",
                help="직접 입력 후 저장. 예: 구분:싱글, 형태:폴타입, 최대하중:9kg",
                width="medium",
            ),
        },
        key=f"editor_{keyword}",
    )

    # 저장 버튼
    if st.button("특징(정리) 저장", type="secondary"):
        current_edits = st.session_state.feature_edits.get(keyword, {}).copy()
        for _, row in edited_df.iterrows():
            rank = row["순위"]
            pid = rank_to_pid.get(rank)
            if pid:
                current_edits[pid] = row.get("특징(정리)", "") or ""
        st.session_state.feature_edits[keyword] = current_edits
        st.success("저장 완료!")

    # 시장 분석 버튼
    st.divider()
    if st.button("시장 분석 →", type="primary", use_container_width=True):
        st.session_state["analyze_keyword"] = keyword
        st.switch_page("pages/2_시장_분석.py")

elif search_clicked and not keyword:
    st.warning("키워드를 입력해주세요.")

# 사이드바: 검색 이력
with st.sidebar:
    st.subheader("검색 이력")
    if st.session_state.search_history:
        for idx, item in enumerate(reversed(st.session_state.search_history[-10:])):
            if st.button(
                f"{item['keyword']} ({item['count']}건)",
                key=f"hist_{idx}_{item['keyword']}_{item['time']}",
            ):
                st.session_state["_reload_keyword"] = item["keyword"]
                st.rerun()
    else:
        st.caption("검색 이력이 없습니다.")
