"""빈집 추천 로직 자체 점검 -- 지금 상태(신호 9개 중 1개만 실 데이터)에서
실제로 어떻게 동작하는지를 고정해 둔다. 신호를 더 붙이면 이 중 일부는
당연히 깨져야 정상(그때 다시 맞게 고치면 됨).
실행: python -m tests.test_vacant_house_match
"""
from src.vacant_house_match import ALL_CRITERIA, USE_TYPE_WEIGHTS, build_location_signals, recommend_top3


def test_only_strategic_industry_signal_is_real_right_now():
    signals = build_location_signals("대덕구", "읍내동")
    filled = [c for c, v in signals.criteria.items() if v is not None]
    assert filled == ["전략산업인접도"], "지금은 전략산업인접도 하나만 실 데이터여야 함 -- 늘었으면 이 테스트를 고칠 것"


def test_strategic_industry_signal_matches_real_company_distribution():
    # data/semiconductor_companies_daejeon.json: 대덕구 41곳(최대) vs 나머지 구 0곳
    assert build_location_signals("대덕구", "읍내동").criteria["전략산업인접도"] == 1.0
    assert build_location_signals("동구", "중앙동").criteria["전략산업인접도"] == 0.0
    assert build_location_signals("중구", "부사동").criteria["전략산업인접도"] == 0.0


def test_use_types_without_the_wired_signal_are_currently_unscoreable():
    signals = build_location_signals("대덕구", "읍내동")
    scoreable = {r.use_type for r in recommend_top3(signals)}
    assert scoreable == {"청년창업공간", "전략산업연계공간"}, (
        "전략산업인접도가 가중치에 없는 문화학습공간/고령자커뮤니티시설/공유주차장은 "
        "coverage 0%라 지금은 절대 추천에 안 나와야 함 -- 이게 지금 시스템의 핵심 한계"
    )


def test_low_coverage_recommendations_are_flagged():
    signals = build_location_signals("대덕구", "읍내동")
    for r in recommend_top3(signals):
        assert r.coverage < 1.0, "지금은 100% coverage인 용도가 있으면 안 됨(신호 하나뿐이므로)"
        assert r.missing_criteria, "빠진 기준이 항상 표시되어야 함"


def demo():
    test_only_strategic_industry_signal_is_real_right_now()
    test_strategic_industry_signal_matches_real_company_distribution()
    test_use_types_without_the_wired_signal_are_currently_unscoreable()
    test_low_coverage_recommendations_are_flagged()
    print("OK - 빈집 추천 로직 자체 점검 통과 (지금은 9개 기준 중 1개만 실데이터인 상태를 고정 확인)")


if __name__ == "__main__":
    demo()
