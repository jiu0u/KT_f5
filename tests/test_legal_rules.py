"""3단계 법적 규칙(별표5의3 R-4-9, 별표19 혼재기준) 자체 점검. 실행: python -m tests.test_legal_rules"""
from src.legal_rules import check_mixing_compatibility, check_water_treatment_reuse


def test_water_treatment_reuse_matches_recycling_industry():
    result = check_water_treatment_reuse("007664-93-9", "폐기물 수집, 운반, 처리 및 원료 재생업")
    assert result.verdict == "가능성있음"


def test_water_treatment_reuse_unknown_for_other_industry():
    result = check_water_treatment_reuse("007664-93-9", "펄프, 종이 및 종이제품 제조업")
    assert result.verdict == "미상"


def test_water_treatment_reuse_not_applicable_for_non_acid():
    result = check_water_treatment_reuse("000108-88-3", "하수, 폐수 및 분뇨 처리업")  # 톨루엔은 산/알칼리 아님
    assert result.verdict == "미적용"


def test_mixing_incompatible_classes():
    # 톨루엔(4류) vs 과산화수소(6류) - 표상 혼재 불가
    result = check_mixing_compatibility("000108-88-3", "007722-84-1")
    assert result.verdict == "미적용"


def test_mixing_same_class_is_unknown_not_incompatible():
    # 표는 서로 다른 유별만 다루므로, 같은 유별끼리는 "불가"로 오판하면 안 됨
    result = check_mixing_compatibility("000108-88-3", "001330-20-7")  # 톨루엔, 자일렌 둘 다 4류
    assert result.verdict == "미상"


def test_mixing_unknown_class():
    result = check_mixing_compatibility("007664-93-9", "000108-88-3")  # 황산은 유별 미상
    assert result.verdict == "미상"


def demo():
    test_water_treatment_reuse_matches_recycling_industry()
    test_water_treatment_reuse_unknown_for_other_industry()
    test_water_treatment_reuse_not_applicable_for_non_acid()
    test_mixing_incompatible_classes()
    test_mixing_same_class_is_unknown_not_incompatible()
    test_mixing_unknown_class()
    print("OK - 3단계 법적 규칙(R-4-9, 혼재기준) 자체 점검 통과")


if __name__ == "__main__":
    demo()
