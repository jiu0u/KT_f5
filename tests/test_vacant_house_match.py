"""빈집 추천 로직 자체 점검 -- 지금 상태(신호 9개 중 4개 실 데이터)에서
실제로 어떻게 동작하는지를 고정해 둔다. 신호를 더 붙이면 이 중 일부는
당연히 깨져야 정상(그때 다시 맞게 고치면 됨).
실행: python -m tests.test_vacant_house_match
"""
from src.vacant_house_match import MIN_COVERAGE, build_location_signals, recommend_top3, score_use_type

REAL_CRITERIA_NOW = {"전략산업인접도", "1인가구비율", "청년인구비율", "고령인구비율"}


def test_exactly_four_signals_are_real_right_now():
    signals = build_location_signals("대덕구", "읍내동")
    filled = {c for c, v in signals.criteria.items() if v is not None}
    assert filled == REAL_CRITERIA_NOW, "늘었으면(혹은 줄었으면) 이 테스트부터 고칠 것"


def test_strategic_industry_signal_matches_real_company_distribution():
    # data/semiconductor_companies_daejeon.json: 대덕구 41곳(최대) vs 나머지 구 0곳
    assert build_location_signals("대덕구", "읍내동").criteria["전략산업인접도"] == 1.0
    assert build_location_signals("동구", "중앙동").criteria["전략산업인접도"] == 0.0
    assert build_location_signals("중구", "부사동").criteria["전략산업인접도"] == 0.0


def test_population_signal_reflects_real_daejeon_demographics():
    # 유성구(대학가)는 청년1인가구 비중이 대전 5개구 중 가장 높아야 함(행안부 실데이터, 202607 기준 53.3%)
    yuseong = build_location_signals("유성구", "진잠동").criteria
    donggu = build_location_signals("동구", "중앙동").criteria
    assert yuseong["청년인구비율"] > donggu["청년인구비율"]
    assert yuseong["고령인구비율"] < donggu["고령인구비율"]


def test_recommendations_now_differ_by_real_district_data():
    # 전략산업 기업이 몰린 대덕구는 전략산업연계공간이 1위, 원도심 고령층 비중이 높은
    # 동구는 고령자커뮤니티시설이 1위여야 함 -- 신호가 1개뿐이던 이전엔 구분이 안 됐던 부분
    daedeok_top = recommend_top3(build_location_signals("대덕구", "읍내동"))[0]
    donggu_top = recommend_top3(build_location_signals("동구", "중앙동"))[0]
    assert daedeok_top.use_type == "전략산업연계공간"
    assert donggu_top.use_type == "고령자커뮤니티시설"


def test_low_coverage_use_types_still_return_no_score():
    # 문화학습공간은 지금 신호 4개 중 1인가구비율(가중치 0.20)만 걸리므로 여전히 coverage 미달
    signals = build_location_signals("대덕구", "읍내동")
    r = score_use_type(signals, "문화학습공간")
    assert r.coverage < MIN_COVERAGE
    assert r.score is None, "coverage 미달이면 score=0이 아니라 None(판단불가)이어야 함"


def test_all_returned_recommendations_meet_min_coverage():
    for district, dong in [("대덕구", "읍내동"), ("동구", "중앙동")]:
        for r in recommend_top3(build_location_signals(district, dong)):
            assert r.coverage >= MIN_COVERAGE
            assert r.missing_criteria, "빠진 기준이 있으면 항상 표시되어야 함(지금은 100% coverage가 없음)"


def demo():
    test_exactly_four_signals_are_real_right_now()
    test_strategic_industry_signal_matches_real_company_distribution()
    test_population_signal_reflects_real_daejeon_demographics()
    test_recommendations_now_differ_by_real_district_data()
    test_low_coverage_use_types_still_return_no_score()
    test_all_returned_recommendations_meet_min_coverage()
    print("OK - 빈집 추천 로직 자체 점검 통과 (신호 9개 중 4개 실데이터, 구별로 실제로 다른 추천 확인)")


if __name__ == "__main__":
    demo()
