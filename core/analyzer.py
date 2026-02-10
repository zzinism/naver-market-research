import json
import os
from dotenv import load_dotenv
from .models import Product, AnalysisResult

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def _get_client():
    from anthropic import Anthropic

    return Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_analysis_prompt(keyword: str, products: list[Product]) -> str:
    product_data = []
    for i, p in enumerate(products):
        product_data.append(
            {
                "rank": i + 1,
                "title": p.title,
                "price": p.lprice,
                "brand": p.brand or "unknown",
                "maker": p.maker or "unknown",
                "mall": p.mall_name,
                "category": f"{p.category1} > {p.category2} > {p.category3}".rstrip(
                    " > "
                ),
            }
        )

    prices = [p.lprice for p in products if p.lprice > 0]
    price_stats = {
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0,
        "avg": int(sum(prices) / len(prices)) if prices else 0,
        "median": sorted(prices)[len(prices) // 2] if prices else 0,
    }

    brands = {}
    for p in products:
        b = p.brand or "unknown"
        brands[b] = brands.get(b, 0) + 1
    top_brands = sorted(brands.items(), key=lambda x: -x[1])[:10]

    prompt = f"""당신은 이커머스 시장 조사 전문 분석가입니다.
네이버 쇼핑에서 "{keyword}" 키워드로 검색한 상위 {len(products)}개 상품 데이터를 분석해주세요.

## 데이터 요약
- 검색 키워드: {keyword}
- 상품 수: {len(products)}개
- 가격 범위: {price_stats['min']:,}원 ~ {price_stats['max']:,}원
- 평균 가격: {price_stats['avg']:,}원
- 중간 가격: {price_stats['median']:,}원
- 주요 브랜드: {', '.join(f'{b}({c}건)' for b, c in top_brands)}

## 상품 목록
{json.dumps(product_data, ensure_ascii=False, indent=1)}

## 분석 요청

아래 JSON 형식으로 분석 결과를 반환하세요. JSON만 반환하고 다른 텍스트는 포함하지 마세요.

{{
  "price_segments": [
    {{
      "range": "가격대 범위 (예: 1만원~3만원)",
      "count": 해당_가격대_상품수,
      "avg_price": 해당_가격대_평균가,
      "characteristics": "이 가격대 상품의 공통 특징",
      "representative_brands": ["브랜드1", "브랜드2"]
    }}
  ],
  "market_overview": "시장 전체 개요 (3-5문장). 가격 분포, 주요 플레이어, 시장 특성 요약",
  "white_space": [
    "시장에서 부족한 영역 1 (구체적으로: 가격대, 기능, 타겟 등)",
    "시장에서 부족한 영역 2",
    "시장에서 부족한 영역 3"
  ],
  "competitive_landscape": "경쟁 구도 분석 (3-5문장). 브랜드 집중도, 가격 경쟁, 차별화 포인트",
  "key_features": ["상품명에서 추출한 주요 특징/기능 키워드 10-15개"]
}}

분석 시 고려사항:
1. 가격 세그먼트는 3~5개로 자연스럽게 나누세요 (데이터 분포 기반)
2. white_space는 실제 사업적으로 활용 가능한 인사이트를 제공하세요
3. key_features는 상품명에 자주 등장하는 마케팅/기능 키워드를 추출하세요
4. 모든 텍스트는 한국어로 작성하세요"""
    return prompt


def _parse_analysis_response(
    keyword: str, products: list[Product], response_text: str
) -> AnalysisResult:
    content = response_text.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    if content.endswith("```"):
        content = content[:-3]

    data = json.loads(content)

    return AnalysisResult(
        keyword=keyword,
        product_count=len(products),
        price_segments=data.get("price_segments", []),
        market_overview=data.get("market_overview", ""),
        white_space=data.get("white_space", []),
        competitive_landscape=data.get("competitive_landscape", ""),
        key_features=data.get("key_features", []),
        raw_ai_response=response_text,
    )


def analyze_market(keyword: str, products: list[Product]) -> AnalysisResult:
    """Claude AI로 시장 분석을 수행합니다."""
    if not ANTHROPIC_API_KEY:
        return _fallback_analysis(keyword, products)

    client = _get_client()
    prompt = _build_analysis_prompt(keyword, products)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    return _parse_analysis_response(keyword, products, response_text)


def _fallback_analysis(keyword: str, products: list[Product]) -> AnalysisResult:
    """API 키 없을 때 규칙 기반 분석을 수행합니다."""
    prices = sorted([p.lprice for p in products if p.lprice > 0])

    if not prices:
        return AnalysisResult(
            keyword=keyword,
            product_count=len(products),
            price_segments=[],
            market_overview="가격 데이터가 없어 분석할 수 없습니다.",
            white_space=[],
            competitive_landscape="",
            key_features=[],
        )

    # 가격대 세그먼트 (4분위)
    n = len(prices)
    quartiles = [prices[0], prices[n // 4], prices[n // 2], prices[3 * n // 4], prices[-1]]
    segments = []
    for i in range(4):
        low, high = quartiles[i], quartiles[i + 1]
        segment_products = [p for p in products if low <= p.lprice <= high]
        brands_in_seg = {}
        for p in segment_products:
            b = p.brand or "unknown"
            brands_in_seg[b] = brands_in_seg.get(b, 0) + 1
        top = sorted(brands_in_seg.items(), key=lambda x: -x[1])[:3]

        segments.append(
            {
                "range": f"{low:,}원 ~ {high:,}원",
                "count": len(segment_products),
                "avg_price": int(sum(p.lprice for p in segment_products) / max(len(segment_products), 1)),
                "characteristics": f"{'저가' if i == 0 else '중저가' if i == 1 else '중고가' if i == 2 else '프리미엄'} 영역",
                "representative_brands": [b for b, _ in top],
            }
        )

    # 브랜드 집중도
    brands = {}
    for p in products:
        b = p.brand or "unknown"
        brands[b] = brands.get(b, 0) + 1
    top_brands = sorted(brands.items(), key=lambda x: -x[1])[:5]
    brand_text = ", ".join(f"{b}({c}건)" for b, c in top_brands)

    # 키워드 추출 (상품명에서 빈번한 단어)
    from collections import Counter

    words = []
    for p in products:
        words.extend(p.title.split())
    word_counts = Counter(words)
    # 1글자, 불용어 제외
    stopwords = {"the", "a", "an", "and", "or", "for", "with", "in", "of", "to", "및", "외", "용"}
    features = [
        w
        for w, c in word_counts.most_common(30)
        if len(w) > 1 and w not in stopwords and c >= 2
    ][:15]

    return AnalysisResult(
        keyword=keyword,
        product_count=len(products),
        price_segments=segments,
        market_overview=f"'{keyword}' 시장은 {min(prices):,}원~{max(prices):,}원 범위에 {len(products)}개 상품이 분포합니다. "
        f"평균 가격은 {int(sum(prices)/len(prices)):,}원이며, 주요 브랜드는 {brand_text}입니다. "
        f"(AI 분석을 위해 ANTHROPIC_API_KEY를 설정해주세요)",
        white_space=["AI API 키를 설정하면 화이트스페이스 분석이 제공됩니다."],
        competitive_landscape=f"상위 브랜드: {brand_text}. 총 {len(brands)}개 브랜드가 경쟁 중입니다.",
        key_features=features,
    )
