import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Streamlit Cloud secrets → 환경변수로 복사 (배포 환경 지원)
try:
    for key in st.secrets:
        if isinstance(st.secrets[key], str):
            os.environ.setdefault(key, st.secrets[key])
except FileNotFoundError:
    pass

st.set_page_config(
    page_title="네이버 쇼핑 시장조사",
    page_icon="🔍",
    layout="wide",
)

st.title("네이버 쇼핑 시장조사 자동화 도구")
st.markdown("키워드 기반으로 네이버 쇼핑 상품을 수집하고, AI로 시장을 분석합니다.")

st.divider()

# API 키 상태 확인
col1, col2 = st.columns(2)

naver_id = os.getenv("NAVER_CLIENT_ID", "")
naver_secret = os.getenv("NAVER_CLIENT_SECRET", "")
anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

with col1:
    st.subheader("API 상태")
    if naver_id and naver_secret:
        st.success("네이버 검색 API: 설정됨")
    else:
        st.error("네이버 검색 API: 미설정 → .env 파일에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 추가 필요")

    if anthropic_key:
        st.success("Claude AI API: 설정됨")
    else:
        st.warning("Claude AI API: 미설정 → AI 분석 없이 기본 통계만 제공됩니다")

with col2:
    st.subheader("사용법")
    st.markdown("""
    1. **키워드 검색**: 왼쪽 메뉴에서 '키워드 검색' 페이지로 이동
    2. **검색 실행**: 키워드를 입력하고 상위 50개 상품 수집
    3. **시장 분석**: AI가 가격 세그먼트, 화이트스페이스, 경쟁 구도를 분석
    4. **비교 분석**: 여러 키워드의 시장을 나란히 비교
    """)

# 세션 상태 초기화
if "search_results" not in st.session_state:
    st.session_state.search_results = {}
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {}
if "search_history" not in st.session_state:
    st.session_state.search_history = []

# 검색 이력 표시
if st.session_state.search_history:
    st.divider()
    st.subheader("최근 검색 이력")
    for item in reversed(st.session_state.search_history[-10:]):
        analyzed = "✅ 분석완료" if item["keyword"] in st.session_state.analysis_results else ""
        st.markdown(f"- **{item['keyword']}** — {item['count']}건 수집 ({item['time']}) {analyzed}")
