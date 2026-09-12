"""3단계 법적 규칙(별표5의3 R-4-9/R-4-6, 별표19 혼재기준) 자체 점검. 실행: python -m tests.test_legal_rules"""
from src.legal_rules import check_mixing_compatibility, check_recycled_solvent_quality, check_water_treatment_reuse


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


def test_mixing_confirmed_not_hazmat():
    # 황산·수산화나트륨은 "모름"이 아니라 "확인된 위험물 아님" - 미적용이어야 함
    result = check_mixing_compatibility("007664-93-9", "000108-88-3")
    assert result.verdict == "미적용"
    assert "황산" in result.note


def test_mixing_unknown_class():
    result = check_mixing_compatibility("000108-88-3", "999999-99-9")  # 존재 안 하는 CAS = 진짜 미상
    assert result.verdict == "미상"


def test_solvent_quality_not_applicable_for_non_solvent():
    result = check_recycled_solvent_quality("007664-93-9")  # 황산은 유기용제 아님
    assert result.verdict == "미적용"


def test_solvent_quality_unknown_without_test_data():
    result = check_recycled_solvent_quality("000108-88-3")  # 톨루엔, 데이터 없음
    assert result.verdict == "미상"


def test_solvent_quality_fails_over_heavy_metal_limit():
    result = check_recycled_solvent_quality(
        "000108-88-3",
        heavy_metals_mg_per_l={"납": 2.0, "비소": 0.1},
        evaporation_residue_pct=0.05,
    )
    assert result.verdict == "미적용"
    assert "납" in result.note


def test_solvent_quality_passes_within_limits():
    result = check_recycled_solvent_quality(
        "000108-88-3",
        heavy_metals_mg_per_l={"납": 0.5, "비소": 0.1},
        evaporation_residue_pct=0.05,
    )
    assert result.verdict == "가능성있음"


def test_isopropanol_needs_purity_and_water_data():
    result = check_recycled_solvent_quality(
        "000067-63-0",  # 2-프로판올
        heavy_metals_mg_per_l={"납": 0.1},
        evaporation_residue_pct=0.05,
    )
    assert result.verdict == "미상"
    assert "순도" in result.note


def test_isopropanol_fails_low_purity():
    result = check_recycled_solvent_quality(
        "000067-63-0",
        heavy_metals_mg_per_l={"납": 0.1},
        evaporation_residue_pct=0.05,
        purity_pct=60.0,
        water_content_pct=5.0,
    )
    assert result.verdict == "미적용"


def demo():
    test_water_treatment_reuse_matches_recycling_industry()
    test_water_treatment_reuse_unknown_for_other_industry()
    test_water_treatment_reuse_not_applicable_for_non_acid()
    test_mixing_incompatible_classes()
    test_mixing_same_class_is_unknown_not_incompatible()
    test_mixing_confirmed_not_hazmat()
    test_mixing_unknown_class()
    test_solvent_quality_not_applicable_for_non_solvent()
    test_solvent_quality_unknown_without_test_data()
    test_solvent_quality_fails_over_heavy_metal_limit()
    test_solvent_quality_passes_within_limits()
    test_isopropanol_needs_purity_and_water_data()
    test_isopropanol_fails_low_purity()
    print("OK - 3단계 법적 규칙(R-4-9, R-4-6, 혼재기준) 자체 점검 통과")


if __name__ == "__main__":
    demo()
