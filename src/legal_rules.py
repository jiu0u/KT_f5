"""3단계 화학·법적 검증 — 딱 두 개 규칙만, 확실히 확인한 조문 범위 안에서 인코딩한다.

CLAUDE.md 3단계 원칙: 2단계 AI 후보를 최종판정하지 않는다. 여기서도 마찬가지 —
아래 두 규칙에 안 걸리면 "적법/부적법"이 아니라 "이 규칙으로는 판단 불가, 직접
확인 필요"라고만 답한다. 없는 근거로 통과·불합격시키지 않는다.

인코딩한 것 (전체 별표가 아니라 이 두 조각만):

1) 폐기물관리법 시행규칙 [별표 5의3] 폐기물의 재활용 기준(제14조의3제1항 관련),
   재활용 유형 R-4-9 — "폐산·폐알칼리를 수처리제로 재활용". 받는 쪽이 하수·폐수·
   분뇨·폐기물 처리시설이면 이 유형이 적용될 가능성이 있음 (오염물질(수소이온농도
   제외) 배출허용기준 충족 등 세부요건은 이 코드로 확인 못 함 — 별도 확인 필요).
   출처: law.go.kr 폐기물관리법 시행규칙 별표5의3 (2019.7.8. 개정)

2) 위험물안전관리법 시행규칙 [별표 19] 유별을 달리하는 위험물의 혼재기준(6x6 표,
   위험물안전관리법 시행령 별표1의 유별 분류가 널리 알려진 소수 물질에만 적용).
   지정수량 1/10 이하에는 이 표가 적용되지 않는다는 비고가 있는데, 취급수량 데이터가
   없어 이 코드는 그 예외를 못 다룬다 — 수량 확인은 별도로 해야 함.

여기 없는 물질/재활용 유형은 전부 "미상"으로 남긴다. 잘못 판단하는 것보다 모른다고
하는 게 낫다.
"""
from dataclasses import dataclass

# 위험물안전관리법 시행령 [별표1] 유별 - 확실히 확인한 물질만 등재.
# 여기 없다고 위험물이 아니라는 뜻은 아니다(단지 이 코드가 모른다는 뜻).
HAZARD_CLASS_BY_CAS = {
    "007722-84-1": 6,  # 과산화 수소 - 제6류(산화성액체)
    "007697-37-2": 6,  # 질산 - 제6류(산화성액체)
    "000108-88-3": 4,  # 톨루엔 - 제4류 제1석유류
    "001330-20-7": 4,  # 자일렌(이성질체 혼합물) - 제4류 제2석유류
    "000067-56-1": 4,  # 메틸 알코올 - 제4류 알코올류
    "000067-63-0": 4,  # 2-프로판올 - 제4류 알코올류
    "000078-93-3": 4,  # 메틸 에틸 케톤 - 제4류 제1석유류
    "000141-78-6": 4,  # 아세트산 에틸 - 제4류 제1석유류
}

# 위험물안전관리법 시행규칙 [별표19] 혼재기준. True = 혼재 가능.
_MIXING_TABLE = {
    1: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
    2: {1: False, 2: False, 3: False, 4: True, 5: True, 6: False},
    3: {1: False, 2: False, 3: False, 4: True, 5: False, 6: False},
    4: {1: False, 2: True, 3: True, 4: False, 5: True, 6: False},
    5: {1: False, 2: True, 3: False, 4: True, 5: False, 6: False},
    6: {1: True, 2: False, 3: False, 4: False, 5: False, 6: False},
}

# 폐산·폐알칼리로 취급 — R-4-9 판단 대상 물질(확실히 산/알칼리인 것만).
ACID_ALKALI_CAS = {"007664-93-9", "007697-37-2", "001310-73-2", "001310-58-3"}
RECYCLING_INDUSTRY_KEYWORDS = ["하수", "폐수", "분뇨", "폐기물"]


@dataclass
class LegalCheckResult:
    rule: str
    verdict: str  # "가능성있음" | "미적용" | "미상"
    note: str


def check_mixing_compatibility(cas_a: str, cas_b: str) -> LegalCheckResult:
    """위험물안전관리법 시행규칙 [별표19] 혼재기준. 유별을 아는 물질끼리만 판단."""
    class_a = HAZARD_CLASS_BY_CAS.get(cas_a)
    class_b = HAZARD_CLASS_BY_CAS.get(cas_b)
    if class_a is None or class_b is None:
        return LegalCheckResult(
            "위험물안전관리법 별표19(혼재기준)", "미상",
            "위험물 유별이 확인된 물질만 판단 가능 - 이 조합 중 유별 미상인 물질이 있음",
        )
    if class_a == class_b:
        return LegalCheckResult(
            "위험물안전관리법 별표19(혼재기준)", "미상",
            f"둘 다 제{class_a}류 - 이 표는 서로 다른 유별 간 혼재만 다룸, 동일 유별 내 세부기준은 별도 확인 필요",
        )
    compatible = _MIXING_TABLE[class_a][class_b]
    return LegalCheckResult(
        "위험물안전관리법 별표19(혼재기준)",
        "가능성있음" if compatible else "미적용",
        f"제{class_a}류-제{class_b}류: {'혼재 가능' if compatible else '혼재 불가'} "
        f"(지정수량 1/10 이하는 이 표 적용 안 됨 - 수량 확인 필요)",
    )


def check_water_treatment_reuse(cas_no: str, receiver_industry: str) -> LegalCheckResult:
    """폐기물관리법 시행규칙 [별표5의3] R-4-9: 폐산·폐알칼리를 수처리제로 재활용."""
    if cas_no not in ACID_ALKALI_CAS:
        return LegalCheckResult("폐기물관리법 별표5의3 R-4-9", "미적용", "폐산·폐알칼리로 확인된 물질이 아님")
    if any(k in receiver_industry for k in RECYCLING_INDUSTRY_KEYWORDS):
        return LegalCheckResult(
            "폐기물관리법 별표5의3 R-4-9", "가능성있음",
            "수처리 관련 업종으로 보임 - 오염물질(pH 제외) 배출허용기준 충족 여부는 별도 확인 필요",
        )
    return LegalCheckResult(
        "폐기물관리법 별표5의3 R-4-9", "미상",
        "수처리 업종이 아님 - R-4-9 외 다른 재활용 유형 해당 여부 직접 확인 필요",
    )
