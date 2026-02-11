import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

st.set_page_config(page_title="시장 분석", page_icon="📊", layout="wide")
st.title("시장 분석")

# 세션 상태 확인
if "search_results" not in st.session_state:
    st.session_state.search_results = {}
if "feature_edits" not in st.session_state:
    st.session_state.feature_edits = {}

available_keywords = list(st.session_state.search_results.keys())

if not available_keywords:
    st.info("먼저 '키워드 검색' 페이지에서 상품을 검색해주세요.")
    st.stop()

# 키워드 선택
default_keyword = st.session_state.get("analyze_keyword", available_keywords[-1])
if default_keyword not in available_keywords:
    default_keyword = available_keywords[-1]

keyword = st.selectbox(
    "분석할 키워드",
    options=available_keywords,
    index=available_keywords.index(default_keyword),
)

products = st.session_state.search_results[keyword]
saved_edits = st.session_state.feature_edits.get(keyword, {})

if not products:
    st.warning("검색 결과가 없습니다.")
    st.stop()

# 특징(정리) 입력 여부 확인
def _feat_text(edit_val) -> str:
    """saved_edits 값에서 features 문자열 추출 (dict/str 호환)"""
    if isinstance(edit_val, dict):
        return edit_val.get("features", "")
    return edit_val or ""

filled_count = sum(1 for p in products if _feat_text(saved_edits.get(p.product_id, "")).strip())

if filled_count == 0:
    st.warning("'키워드 검색' 페이지에서 각 상품의 **특징(정리)**를 입력하고 저장해주세요.")
    st.caption("입력 형식: `구분:싱글, 형태:폴타입, 최대하중:9kg`")
    st.stop()


# ─── key:value 파싱 ───
def parse_features(text: str) -> dict[str, str]:
    """'구분:싱글, 형태:폴타입' → {'구분': '싱글', '형태': '폴타입'}"""
    result = {}
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            key, val = key.strip(), val.strip()
            if key and val:
                result[key] = val
    return result


# 전체 데이터 파싱
all_rows = []
for p in products:
    if p.lprice <= 0:
        continue
    user_text = _feat_text(saved_edits.get(p.product_id, "")).strip()
    if not user_text:
        continue
    features = parse_features(user_text)
    for key, val in features.items():
        all_rows.append({
            "상품명": p.title,
            "가격": p.lprice,
            "브랜드": p.brand or "(브랜드 없음)",
            "판매처": p.mall_name,
            "분류 기준": key,
            "값": val,
        })

if not all_rows:
    st.warning("파싱된 특징이 없습니다. `key:value` 형식으로 입력했는지 확인해주세요.")
    st.caption("예: `구분:싱글, 형태:폴타입, 최대하중:9kg`")
    st.stop()

df_all = pd.DataFrame(all_rows)

# ─── KPI 카드 ───
prices = [p.lprice for p in products if p.lprice > 0]
st.divider()

c1, c2, c3, c4 = st.columns(4)
c1.metric("상품 수", f"{len(products)}건")
c2.metric("최저가", f"{min(prices):,}원" if prices else "-")
c3.metric("최고가", f"{max(prices):,}원" if prices else "-")
c4.metric("평균가", f"{int(sum(prices) / len(prices)):,}원" if prices else "-")

st.caption(f"특징(정리) 입력 완료: {filled_count}/{len(products)}건")

st.divider()

# ─── 분류 기준 선택 (탭) ───
categories = df_all["분류 기준"].unique().tolist()

tabs = st.tabs(categories)

for tab, cat in zip(tabs, categories):
    with tab:
        df_cat = df_all[df_all["분류 기준"] == cat]

        # 값별 빈도순 정렬
        value_order = df_cat["값"].value_counts().index.tolist()
        value_order.reverse()

        # ─── 스캐터 플롯: X=가격, Y=값 ───
        st.subheader(f"'{cat}' 기준 × 가격 분포")
        st.caption("각 점은 해당 값을 가진 제품입니다.")

        fig = px.strip(
            df_cat,
            x="가격",
            y="값",
            color="브랜드",
            hover_data=["상품명", "판매처"],
            category_orders={"값": value_order},
            labels={"가격": "가격 (원)", "값": cat},
        )
        fig.update_traces(
            marker=dict(size=10, opacity=0.7),
            jitter=0.3,
        )
        chart_height = max(300, len(value_order) * 40 + 100)
        fig.update_layout(
            height=chart_height,
            xaxis=dict(title="가격 (원)", tickformat=","),
            yaxis=dict(title=cat),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, title=None,
            ),
            margin=dict(l=120),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ─── 값별 가격 통계 ───
        st.markdown(f"**'{cat}' 값별 가격 통계**")
        stats = []
        for val in reversed(value_order):
            vp = df_cat[df_cat["값"] == val]["가격"]
            stats.append({
                cat: val,
                "제품 수": len(vp),
                "최저가": f"{int(vp.min()):,}원",
                "최고가": f"{int(vp.max()):,}원",
                "평균가": f"{int(vp.mean()):,}원",
            })
        st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)

        # ─── 값별 비율 파이 차트 + 브랜드 분포 ───
        col_pie, col_brand = st.columns(2)

        with col_pie:
            st.markdown(f"**'{cat}' 비율**")
            val_counts = df_cat["값"].value_counts().reset_index()
            val_counts.columns = [cat, "제품 수"]
            fig_pie = px.pie(val_counts, names=cat, values="제품 수")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_brand:
            st.markdown(f"**'{cat}' × 브랜드**")
            brand_val = (
                df_cat.groupby(["값", "브랜드"])
                .size()
                .reset_index(name="제품 수")
            )
            fig_bar = px.bar(
                brand_val,
                x="값",
                y="제품 수",
                color="브랜드",
                labels={"값": cat},
            )
            fig_bar.update_layout(
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, title=None,
                ),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
