"""시장조사 데이터 Convex DB 연동 클라이언트"""
import json
import os
from dotenv import load_dotenv
from .models import Product, AnalysisResult

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env.local"))

CONVEX_URL = os.getenv("CONVEX_URL", "https://giddy-rhinoceros-903.convex.cloud")


def _get_client():
    from convex import ConvexClient
    return ConvexClient(CONVEX_URL)


def save_search(keyword: str, sort_type: str, products: list[Product]) -> str:
    """검색 세션과 상품 데이터를 Convex에 저장합니다. 세션 ID를 반환합니다."""
    client = _get_client()

    prices = [p.lprice for p in products if p.lprice > 0]

    # 1) 세션 생성
    session_id = client.mutation("searchSessions:create", {
        "keyword": keyword,
        "sortType": sort_type,
        "productCount": len(products),
        "minPrice": min(prices) if prices else 0,
        "maxPrice": max(prices) if prices else 0,
        "avgPrice": int(sum(prices) / len(prices)) if prices else 0,
    })

    # 2) 상품 삽입
    for i, p in enumerate(products):
        client.mutation("searchProducts:insert", {
            "sessionId": session_id,
            "rank": i + 1,
            "title": p.title,
            "link": p.link,
            "image": p.image,
            "lprice": p.lprice,
            "hprice": p.hprice,
            "mallName": p.mall_name,
            "naverProductId": p.product_id,
            "productType": p.product_type,
            "brand": p.brand,
            "maker": p.maker,
            "category1": p.category1,
            "category2": p.category2,
            "category3": p.category3,
            "category4": p.category4,
        })

    return session_id


def save_analysis(session_id: str, result: AnalysisResult) -> str:
    """AI 분석 결과를 Convex에 저장합니다."""
    client = _get_client()

    analysis_id = client.mutation("marketAnalysis:insert", {
        "sessionId": session_id,
        "keyword": result.keyword,
        "productCount": result.product_count,
        "priceSegments": json.dumps(result.price_segments, ensure_ascii=False),
        "marketOverview": result.market_overview,
        "whiteSpace": json.dumps(result.white_space, ensure_ascii=False),
        "competitiveLandscape": result.competitive_landscape,
        "keyFeatures": json.dumps(result.key_features, ensure_ascii=False),
        "rawAiResponse": result.raw_ai_response or None,
    })

    return analysis_id


def get_recent_sessions(limit: int = 20) -> list:
    """최근 검색 세션 목록을 가져옵니다."""
    client = _get_client()
    return client.query("searchSessions:getRecent", {"limit": limit})


def get_session_products(session_id: str) -> list:
    """세션의 상품 데이터를 가져옵니다."""
    client = _get_client()
    return client.query("searchProducts:getBySession", {"sessionId": session_id})


def get_session_analysis(session_id: str) -> dict | None:
    """세션의 분석 결과를 가져옵니다."""
    client = _get_client()
    return client.query("marketAnalysis:getBySession", {"sessionId": session_id})
