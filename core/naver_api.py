import os
import re
import requests
from dotenv import load_dotenv
from .models import Product

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def search_products(query: str, display: int = 50, sort: str = "sim") -> list[Product]:
    """
    네이버 쇼핑 검색 API로 상품을 검색합니다.

    Args:
        query: 검색 키워드
        display: 결과 수 (1-100, 기본 50)
        sort: sim(관련도), date(날짜), asc(가격↑), dsc(가격↓)

    Returns:
        Product 리스트

    Raises:
        ValueError: API 키 미설정
        requests.HTTPError: API 호출 실패
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise ValueError(
            "NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET이 .env에 설정되어야 합니다."
        )

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": min(display, 100),
        "start": 1,
        "sort": sort,
    }

    resp = requests.get(SEARCH_URL, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    products = []
    for item in data.get("items", []):
        products.append(
            Product(
                title=strip_html(item.get("title", "")),
                link=item.get("link", ""),
                image=item.get("image", ""),
                lprice=int(item.get("lprice", 0) or 0),
                hprice=int(item.get("hprice", 0) or 0),
                mall_name=item.get("mallName", ""),
                product_id=str(item.get("productId", "")),
                product_type=str(item.get("productType", "")),
                brand=item.get("brand", ""),
                maker=item.get("maker", ""),
                category1=item.get("category1", ""),
                category2=item.get("category2", ""),
                category3=item.get("category3", ""),
                category4=item.get("category4", ""),
            )
        )

    return products


# ─── 상품명에서 주요 특징 추출 ───

_SIZE_PATTERN = re.compile(
    r'\d{2,4}\s*[xX×*]\s*\d{2,4}(?:\s*[xX×*]\s*\d{2,4})?'  # 1200x600, 120*60*72
    r'|\d{2,4}\s*(?:mm|cm|m)\b'                               # 120cm, 1200mm
    r'|\d{2,3}\s*(?:인치|형)\b'                                # 27인치, 32형
)

_COLOR_KEYWORDS = [
    "화이트", "블랙", "그레이", "아이보리", "우드", "월넛", "오크", "메이플",
    "브라운", "베이지", "네이비", "레드", "블루", "그린", "핑크", "옐로우",
    "실버", "골드", "로즈골드", "차콜", "크림", "라이트그레이", "다크그레이",
    "내추럴", "빈티지", "앤틱", "에쉬", "소노마", "라떼",
]

_MATERIAL_KEYWORDS = [
    "원목", "강화유리", "스틸", "알루미늄", "철제", "메탈",
    "MDF", "PB", "LPM", "HPL", "멜라민", "하이글로시", "포밍",
    "패브릭", "메쉬", "가죽", "인조가죽", "PU", "PVC",
    "대나무", "합판", "집성목", "파티클보드",
]

_FEATURE_KEYWORDS = [
    "전동", "높낮이조절", "높낮이", "각도조절", "틸팅",
    "모션데스크", "스탠딩", "리프트", "승강",
    "USB", "콘센트", "무선충전", "LED",
    "수납", "서랍", "선반", "거치대",
    "접이식", "이동식", "바퀴", "캐스터",
    "헤드레스트", "팔걸이", "럼버서포트", "풋레스트",
    "인체공학", "듀얼모니터", "모니터암",
    "강화도어", "슬라이딩", "책장", "파티션",
]

_TYPE_KEYWORDS = [
    "게이밍", "사무용", "학생용", "컴퓨터", "독서",
    "회의", "좌식", "입식", "코너", "L자", "ㄱ자",
    "1인용", "2인용", "4인용", "6인용",
    "싱글", "슈퍼싱글", "퀸", "킹",
]


def extract_features(title: str) -> dict[str, str]:
    """상품명에서 크기, 색상, 소재, 기능, 유형을 추출합니다."""
    features = {}

    # 크기
    size_match = _SIZE_PATTERN.search(title)
    if size_match:
        features["크기"] = size_match.group().strip()

    # 색상
    colors = [c for c in _COLOR_KEYWORDS if c in title]
    if colors:
        features["색상"] = ", ".join(colors)

    # 소재
    materials = [m for m in _MATERIAL_KEYWORDS if m.lower() in title.lower()]
    if materials:
        features["소재"] = ", ".join(materials)

    # 기능
    funcs = [f for f in _FEATURE_KEYWORDS if f in title]
    if funcs:
        features["기능"] = ", ".join(funcs)

    # 유형
    types = [t for t in _TYPE_KEYWORDS if t in title]
    if types:
        features["유형"] = ", ".join(types)

    return features


def features_to_str(title: str) -> str:
    """상품명에서 추출한 특징을 한 줄 문자열로 반환합니다."""
    feat = extract_features(title)
    if not feat:
        return "-"
    return " | ".join(f"{k}:{v}" for k, v in feat.items())
