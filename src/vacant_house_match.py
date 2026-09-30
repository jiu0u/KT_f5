"""빈집 활용 추천 로직 뼈대 -- CLAUDE.md 원래 파이프라인의 TOPSIS 랭킹을
"물질별 처리업체 순위"에서 "빈집 하나에 대한 활용방안(용도) 순위"로 뒤집은 버전.

**지금 단계의 진짜 상태(중요)**: 아래 9개 판단 기준(criteria) 중 실제 데이터로
채워진 건 `전략산업인접도` 하나뿐이다(`data/semiconductor_companies_daejeon.json`
기반, 구 단위 집계). 나머지 8개(청년/고령인구비율, 1인가구비율, 유동인구,
상권밀도, 생활SOC밀도, 주차장부족도, 교통접근성)는 아직 실제 데이터를 못
붙여서 전부 None(미확보)이다. 그래서 지금 이 모듈로 나오는 추천은 "로직이
작동은 하는지" 확인용이지, 실제로 신뢰할 수 있는 추천이 아니다 -- 용도별로
coverage(가중치 기준 데이터 확보 비율)가 항상 같이 나오는 이유가 이것이다.
"""
from dataclasses import dataclass, field
from pathlib import Path
import json

DATA_DIR = Path(__file__).parent.parent / "data"

# 용도별 판단기준과 가중치. 가중치는 도메인 전문가 검증 없이 상식적으로 잡은
# 추정치다 -- legal_rules.py의 "미상"과 같은 취지로, 근거 없는 정밀함을 주장하지 않는다.
USE_TYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "청년창업공간": {"청년인구비율": 0.30, "유동인구": 0.25, "상권밀도": 0.25, "전략산업인접도": 0.20},
    "문화학습공간": {"생활SOC밀도": 0.40, "1인가구비율": 0.20, "교통접근성": 0.20, "유동인구": 0.20},
    "고령자커뮤니티시설": {"고령인구비율": 0.45, "1인가구비율": 0.25, "생활SOC밀도": 0.20, "교통접근성": 0.10},
    "공유주차장": {"주차장부족도": 0.45, "상권밀도": 0.35, "교통접근성": 0.20},
    "전략산업연계공간": {"전략산업인접도": 0.60, "교통접근성": 0.25, "상권밀도": 0.15},
}

ALL_CRITERIA = sorted({c for w in USE_TYPE_WEIGHTS.values() for c in w})


@dataclass
class LocationSignals:
    district: str
    dong: str
    criteria: dict[str, float | None] = field(default_factory=dict)  # 0~1 정규화, None=미확보


@dataclass
class Recommendation:
    use_type: str
    score: float | None      # coverage가 0이면 None (판단 불가)
    coverage: float          # 이 용도의 가중치 중 실제 데이터로 채워진 비율 (0~1)
    used_criteria: list[str]
    missing_criteria: list[str]


def _strategic_industry_density_by_district() -> dict[str, float]:
    """구별 반도체 관련 기업 수를 0~1로 정규화 -- 지금 유일하게 실 데이터인 신호."""
    path = DATA_DIR / "semiconductor_companies_daejeon.json"
    companies = json.loads(path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for c in companies:
        counts[c["district"]] = counts.get(c["district"], 0) + 1
    max_count = max(counts.values(), default=1)
    return {district: n / max_count for district, n in counts.items()}


def build_location_signals(district: str, dong: str) -> LocationSignals:
    density = _strategic_industry_density_by_district()
    criteria: dict[str, float | None] = {c: None for c in ALL_CRITERIA}
    criteria["전략산업인접도"] = density.get(district, 0.0)  # 데이터에 없는 구는 0(실제로 기업이 0곳)
    return LocationSignals(district=district, dong=dong, criteria=criteria)


def score_use_type(signals: LocationSignals, use_type: str) -> Recommendation:
    weights = USE_TYPE_WEIGHTS[use_type]
    used, missing, weighted_sum, available_weight = [], [], 0.0, 0.0
    for criterion, weight in weights.items():
        value = signals.criteria.get(criterion)
        if value is None:
            missing.append(criterion)
            continue
        used.append(criterion)
        weighted_sum += weight * value
        available_weight += weight

    coverage = available_weight / sum(weights.values())
    score = (weighted_sum / available_weight) if available_weight > 0 else None
    return Recommendation(use_type, score, coverage, used, missing)


def recommend_top3(signals: LocationSignals) -> list[Recommendation]:
    scored = [score_use_type(signals, ut) for ut in USE_TYPE_WEIGHTS]
    # coverage가 0(판단 근거가 아예 없음)인 용도는 순위에서 제외 -- 점수를 0으로 깔고 순위 매기면
    # "데이터가 없어서 낮게 나온 것"과 "데이터상 실제로 안 맞는 것"이 구분 안 되기 때문
    ranked = sorted((r for r in scored if r.score is not None), key=lambda r: -r.score)
    return ranked[:3]
