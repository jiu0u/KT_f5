"""교통사고 위험지점 예측 로직 자체 점검. 실행: python -m tests.test_predict_accident_risk_candidates"""
from scripts.predict_accident_risk_candidates import HIGH_DENSITY_DISTRICTS, build, width_bucket
from src.accident_risk import load_low_density_districts


def test_road_width_zero_is_treated_as_missing_not_narrow():
    # 대전 roadBt가 전부 "0"이라 0은 "정보없음"이어야지 "6m미만(좁음)"으로 잘못 집계되면 안 됨
    assert width_bucket(0.0) == "도로폭정보없음"
    assert width_bucket(None) == "도로폭정보없음"
    assert width_bucket(5.0) == "6m미만(좁음)"


def test_high_and_low_density_districts_do_not_overlap():
    low = load_low_density_districts()
    assert not (HIGH_DENSITY_DISTRICTS & low), "고밀도 기준 구가 저밀도 집합에도 들어있으면 학습-적용이 섞임"


def test_candidates_are_only_from_low_density_unrecorded_locations():
    candidates = build()
    low = load_low_density_districts()
    assert len(candidates) > 0
    assert all(c["district"] in low for c in candidates)
    assert all(not c["is_known_hotspot"] for c in candidates), "이미 사고다발로 확인된 지점이 '예측 후보'에 섞이면 안 됨"


def demo():
    test_road_width_zero_is_treated_as_missing_not_narrow()
    test_high_and_low_density_districts_do_not_overlap()
    test_candidates_are_only_from_low_density_unrecorded_locations()
    print("OK - 교통사고 위험지점 예측 자체 점검 통과")


if __name__ == "__main__":
    demo()
