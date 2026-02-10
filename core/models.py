from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Product:
    title: str
    link: str
    image: str
    lprice: int
    hprice: int
    mall_name: str
    product_id: str
    product_type: str
    brand: str
    maker: str
    category1: str
    category2: str
    category3: str
    category4: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnalysisResult:
    keyword: str
    product_count: int
    price_segments: list[dict]
    market_overview: str
    white_space: list[str]
    competitive_landscape: str
    key_features: list[str]
    raw_ai_response: str = ""
