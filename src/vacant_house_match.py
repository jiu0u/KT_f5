"""빈집 활용 추천 로직 뼈대 -- CLAUDE.md 원래 파이프라인의 TOPSIS 랭킹을
"물질별 처리업체 순위"에서 "빈집 하나에 대한 활용방안(용도) 순위"로 뒤집은 버전.

**지금 단계의 진짜 상태(중요)**: 아래 9개 판단 기준(criteria) 중 실제 데이터로
채워진 건 6개 -- `전략산업인접도`(반도체 관련 기업 구별 분포), `1인가구비율`/
`청년인구비율`/`고령인구비율`(행안부 주민등록 API, `scripts/build_daejeon_population_signals.py`),
`상권밀도`(소상공인시장진흥공단 상가업소 수, `scripts/build_daejeon_commercial_density.py`),
`주차장부족도`(전국주차장정보 표준데이터, `scripts/build_daejeon_parking_supply.py`).
나머지 3개(유동인구, 생활SOC밀도, 교통접근성)는 아직 못 붙여서 None(미확보)이다.
`청년/고령인구비율`은 이름과 달리 **전체 인구가 아니라 1인가구 중** 연령대
비중이고, `상권밀도`도 이름과 달리 면적/인구로 나눈 진짜 밀도가 아니라 구별
상가업소 총 개수를 정규화한 것이며, `주차장부족도`는 실제 수요 대비 부족량이
아니라 공급량(주차구획수)의 역수로 근사한 것이다 -- 셋 다 실제 한계로 각
build 스크립트에 명시해 뒀다. 그래서 지금 이 모듈로 나오는 추천은 "로직이
작동은 하는지" 확인용에 가깝지, 아직 전적으로 신뢰할 수 있는 추천은 아니다 --
용도별로 coverage(가중치 기준 데이터 확보 비율)가 항상 같이 나오는 이유가 이것이다.
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

# coverage가 이 밑이면 score를 아예 안 낸다. 신호가 1~2개뿐일 때 renormalize를 그대로
# 쓰면(가중치 대비 실제로 가진 것만으로 나눔) 그 하나가 최댓값이기만 해도 무조건 만점이
# 나와서 서로 다른 용도가 동점 처리되는 왜곡이 실제로 있었다(대덕구 읍내동 사례,
# 청년창업공간·전략산업연계공간 둘 다 1.000). 최소 절반 이상 근거가 있어야 점수를 믿는다.
MIN_COVERAGE = 0.5


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


def _population_signals_by_district() -> dict[str, dict]:
    path = DATA_DIR / "daejeon_population_signals.json"
    if not path.exists():
        return {}  # scripts/build_daejeon_population_signals.py 아직 안 돌렸으면 전부 미확보로 처리
    return {r["district"]: r for r in json.loads(path.read_text(encoding="utf-8"))}


def _commercial_density_by_district() -> dict[str, float]:
    """구별 상가업소 수를 0~1로 정규화 -- 이름은 밀도지만 실제론 총량(모듈 docstring 참고)."""
    path = DATA_DIR / "daejeon_commercial_density.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    max_count = max((r["store_count"] for r in rows), default=1)
    return {r["district"]: r["store_count"] / max_count for r in rows}


def _parking_scarcity_by_district() -> dict[str, float]:
    """구별 주차구획수를 0~1로 정규화한 뒤 뒤집음(공급 적을수록 부족도 높음) -- 수요 데이터 없는 약한 근사."""
    path = DATA_DIR / "daejeon_parking_supply.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    max_capacity = max((r["capacity"] for r in rows), default=1)
    return {r["district"]: 1 - (r["capacity"] / max_capacity) for r in rows}


def build_location_signals(district: str, dong: str) -> LocationSignals:
    density = _strategic_industry_density_by_district()
    population = _population_signals_by_district()
    commercial = _commercial_density_by_district()
    parking = _parking_scarcity_by_district()

    criteria: dict[str, float | None] = {c: None for c in ALL_CRITERIA}
    criteria["전략산업인접도"] = density.get(district, 0.0)  # 데이터에 없는 구는 0(실제로 기업이 0곳)
    if district in population:
        p = population[district]
        criteria["1인가구비율"] = p["one_person_household_ratio"]
        # 이름은 "청년/고령인구비율"이지만 실제로는 1인가구 중 연령대 비중(전체 인구 아님) -- 모듈 docstring 참고
        criteria["청년인구비율"] = p["youth_one_person_household_ratio"]
        criteria["고령인구비율"] = p["elderly_one_person_household_ratio"]
    if district in commercial:
        criteria["상권밀도"] = commercial[district]
    if district in parking:
        criteria["주차장부족도"] = parking[district]
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
    # coverage 미달이면 score는 항상 None -- "근거 부족"과 "실제로 낮은 점수"를 구조적으로 분리
    score = (weighted_sum / available_weight) if coverage >= MIN_COVERAGE else None
    return Recommendation(use_type, score, coverage, used, missing)


def recommend_top3(signals: LocationSignals) -> list[Recommendation]:
    scored = [score_use_type(signals, ut) for ut in USE_TYPE_WEIGHTS]
    # score가 None인 용도(coverage 미달 포함)는 순위에서 제외 -- 점수를 0으로 깔고 순위 매기면
    # "데이터가 없어서 낮게 나온 것"과 "데이터상 실제로 안 맞는 것"이 구분 안 되기 때문
    ranked = sorted((r for r in scored if r.score is not None), key=lambda r: -r.score)
    return ranked[:3]
