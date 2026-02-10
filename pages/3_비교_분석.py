import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

st.set_page_config(page_title="비교 분석", page_icon="⚖️", layout="wide")
st.title("비교 분석")

# 세션 상태 확인
if "search_results" not in st.session_state:
    st.session_state.search_results = {}
if "feature_edits" not in st.session_state:
    st.session_state.feature_edits = {}

available = list(st.session_state.search_results.keys())

if len(available) < 2:
    st.info("비교 분석을 위해 2개 이상의 키워드를 검색해주세요. ('키워드 검색' 페이지에서 추가 검색)")
    st.stop()

# 키워드 2개 선택
col1, col2 = st.columns(2)
with col1:
    kw1 = st.selectbox("키워드 1", options=available, index=0)
with col2:
    remaining = [k for k in available if k != kw1]
    kw2 = st.selectbox("키워드 2", options=remaining, index=0)

products1 = st.session_state.search_results[kw1]
products2 = st.session_state.search_results[kw2]

st.divider()

# KPI 비교
st.subheader("기본 지표 비교")
prices1 = [p.lprice for p in products1 if p.lprice > 0]
prices2 = [p.lprice for p in products2 if p.lprice > 0]

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(f"상품 수", "")
    st.markdown(f"**{kw1}**: {len(products1)}건")
    st.markdown(f"**{kw2}**: {len(products2)}건")

with c2:
    st.metric("최저가", "")
    st.markdown(f"**{kw1}**: {min(prices1):,}원" if prices1 else f"**{kw1}**: -")
    st.markdown(f"**{kw2}**: {min(prices2):,}원" if prices2 else f"**{kw2}**: -")

with c3:
    st.metric("최고가", "")
    st.markdown(f"**{kw1}**: {max(prices1):,}원" if prices1 else f"**{kw1}**: -")
    st.markdown(f"**{kw2}**: {max(prices2):,}원" if prices2 else f"**{kw2}**: -")

with c4:
    avg1 = int(sum(prices1) / len(prices1)) if prices1 else 0
    avg2 = int(sum(prices2) / len(prices2)) if prices2 else 0
    st.metric("평균가", "")
    st.markdown(f"**{kw1}**: {avg1:,}원")
    st.markdown(f"**{kw2}**: {avg2:,}원")

st.divider()

# 가격 분포 오버레이
st.subheader("가격 분포 비교")
fig = go.Figure()
fig.add_trace(go.Histogram(x=prices1, name=kw1, opacity=0.7, nbinsx=20))
fig.add_trace(go.Histogram(x=prices2, name=kw2, opacity=0.7, nbinsx=20))
fig.update_layout(
    barmode="overlay",
    xaxis_title="가격 (원)",
    yaxis_title="상품 수",
    legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# 브랜드 비교
st.subheader("브랜드 비교")

col_b1, col_b2 = st.columns(2)


def get_brand_counts(products):
    brands = {}
    for p in products:
        b = p.brand or "(브랜드 없음)"
        brands[b] = brands.get(b, 0) + 1
    return sorted(brands.items(), key=lambda x: -x[1])


brands1 = get_brand_counts(products1)
brands2 = get_brand_counts(products2)

with col_b1:
    st.markdown(f"**{kw1}** 상위 브랜드")
    df_b1 = pd.DataFrame(brands1[:10], columns=["브랜드", "상품수"])
    fig_b1 = px.bar(df_b1, x="브랜드", y="상품수", title=kw1)
    st.plotly_chart(fig_b1, use_container_width=True)

with col_b2:
    st.markdown(f"**{kw2}** 상위 브랜드")
    df_b2 = pd.DataFrame(brands2[:10], columns=["브랜드", "상품수"])
    fig_b2 = px.bar(df_b2, x="브랜드", y="상품수", title=kw2)
    st.plotly_chart(fig_b2, use_container_width=True)

# 공통 브랜드
set1 = {b for b, _ in brands1 if b != "(브랜드 없음)"}
set2 = {b for b, _ in brands2 if b != "(브랜드 없음)"}
common = set1 & set2

if common:
    st.markdown(f"**공통 브랜드** ({len(common)}개): {', '.join(sorted(common))}")
    st.markdown(f"**{kw1}에만 있는 브랜드**: {', '.join(sorted(set1 - set2)[:10])}")
    st.markdown(f"**{kw2}에만 있는 브랜드**: {', '.join(sorted(set2 - set1)[:10])}")

st.divider()

# ─── 특징(정리) 비교 (key:value 구조) ───
st.subheader("특징(정리) 비교")

edits1 = st.session_state.feature_edits.get(kw1, {})
edits2 = st.session_state.feature_edits.get(kw2, {})

filled1 = sum(1 for p in products1 if edits1.get(p.product_id, "").strip())
filled2 = sum(1 for p in products2 if edits2.get(p.product_id, "").strip())


def parse_features(text: str) -> dict[str, str]:
    result = {}
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            key, val = key.strip(), val.strip()
            if key and val:
                result[key] = val
    return result


def collect_feature_data(products, edits):
    """key별 value 빈도를 수집. {key: {val: count}}"""
    data = {}
    for p in products:
        text = edits.get(p.product_id, "").strip()
        if not text:
            continue
        for key, val in parse_features(text).items():
            data.setdefault(key, {})
            data[key][val] = data[key].get(val, 0) + 1
    return data


if filled1 > 0 and filled2 > 0:
    feat_data1 = collect_feature_data(products1, edits1)
    feat_data2 = collect_feature_data(products2, edits2)

    all_keys = sorted(set(feat_data1.keys()) | set(feat_data2.keys()))

    if not all_keys:
        st.info("파싱된 특징이 없습니다.")
    else:
        compare_tabs = st.tabs(all_keys)
        for ctab, key in zip(compare_tabs, all_keys):
            with ctab:
                vals1 = feat_data1.get(key, {})
                vals2 = feat_data2.get(key, {})
                all_vals = sorted(set(vals1.keys()) | set(vals2.keys()))

                compare_rows = []
                for v in all_vals:
                    compare_rows.append({
                        key: v,
                        kw1: vals1.get(v, 0),
                        kw2: vals2.get(v, 0),
                    })
                df_cmp = pd.DataFrame(compare_rows)

                fig_cmp = go.Figure()
                fig_cmp.add_trace(go.Bar(
                    x=df_cmp[key], y=df_cmp[kw1],
                    name=kw1, marker_color="#636EFA",
                ))
                fig_cmp.add_trace(go.Bar(
                    x=df_cmp[key], y=df_cmp[kw2],
                    name=kw2, marker_color="#EF553B",
                ))
                fig_cmp.update_layout(
                    barmode="group",
                    xaxis_title=key,
                    yaxis_title="제품 수",
                    legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
                )
                st.plotly_chart(fig_cmp, use_container_width=True)

                st.dataframe(df_cmp, use_container_width=True, hide_index=True)

elif filled1 == 0 and filled2 == 0:
    st.info("두 키워드 모두 '특징(정리)' 데이터가 없습니다. 키워드 검색 페이지에서 입력해주세요.")
elif filled1 == 0:
    st.info(f"'{kw1}' 키워드의 '특징(정리)' 데이터가 없습니다.")
else:
    st.info(f"'{kw2}' 키워드의 '특징(정리)' 데이터가 없습니다.")
