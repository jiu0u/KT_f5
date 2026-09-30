"""빈집 추천 로직 자체 점검 -- 지금 상태(신호 9개 중 6개 실 데이터)에서
실제로 어떻게 동작하는지를 고정해 둔다. 신호를 더 붙이면 이 중 일부는
당연히 깨져야 정상(그때 다시 맞게 고치면 됨).
실행: python -m tests.test_vacant_house_match
"""
from src.vacant_house_match import MIN_COVERAGE, build_location_signals, recommend_top3, score_use_type

REAL_CRITERIA_NOW = {"전략산업인접도", "1인가구비율", "청년인구비율", "고령인구비율", "상권밀도", "주차장부족도"}


def test_exactly_six_signals_are_real_right_now():
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


def test_commercial_density_signal_matches_real_store_counts():
    # data/daejeon_commercial_density.json: 서구 27,753개(최대) vs 대덕구 8,503개(최소)
    assert build_location_signals("서구", "도마동").criteria["상권밀도"] == 1.0
    assert build_location_signals("대덕구", "읍내동").criteria["상권밀도"] < build_location_signals("서구", "도마동").criteria["상권밀도"]


def test_low_coverage_use_types_still_return_no_score():
    # 문화학습공간(상권밀도가 가중치에 없음)은 여전히 1인가구비율(0.20)만 걸려 coverage 미달
    signals = build_location_signals("대덕구", "읍내동")
    r = score_use_type(signals, "문화학습공간")
    assert r.coverage < MIN_COVERAGE
    assert r.score is None, "coverage 미달이면 score=0이 아니라 None(판단불가)이어야 함"


def test_parking_scarcity_signal_matches_real_capacity_data():
    # data/daejeon_parking_supply.json: 중구가 주차면수 최다(6,428면)라 부족도는 가장 낮아야 함
    jung = build_location_signals("중구", "부사동").criteria["주차장부족도"]
    daedeok = build_location_signals("대덕구", "읍내동").criteria["주차장부족도"]  # 주차면수 최소(1,501면)
    assert jung < daedeok


def test_gongyu_parking_now_scoreable_with_six_signals():
    # 공유주차장은 상권밀도(0.35)+주차장부족도(0.45)=coverage 80%로 이제 MIN_COVERAGE를 넘는다
    # -- 신호 4개였을 때는 35%로 문턱을 못 넘었던 용도(테스트 기록용)
    signals = build_location_signals("서구", "도마동")
    r = score_use_type(signals, "공유주차장")
    assert r.coverage >= MIN_COVERAGE
    assert r.score is not None


def test_all_returned_recommendations_meet_min_coverage():
    for district, dong in [("대덕구", "읍내동"), ("동구", "중앙동")]:
        for r in recommend_top3(build_location_signals(district, dong)):
            assert r.coverage >= MIN_COVERAGE
            assert r.missing_criteria, "빠진 기준이 있으면 항상 표시되어야 함(지금은 100% coverage가 없음)"


def demo():
    test_exactly_six_signals_are_real_right_now()
    test_strategic_industry_signal_matches_real_company_distribution()
    test_population_signal_reflects_real_daejeon_demographics()
    test_commercial_density_signal_matches_real_store_counts()
    test_recommendations_now_differ_by_real_district_data()
    test_low_coverage_use_types_still_return_no_score()
    test_parking_scarcity_signal_matches_real_capacity_data()
    test_gongyu_parking_now_scoreable_with_six_signals()
    test_all_returned_recommendations_meet_min_coverage()
    print("OK - 빈집 추천 로직 자체 점검 통과 (신호 9개 중 6개 실데이터, 5개 용도 중 4개 이제 추천 가능)")


if __name__ == "__main__":
    demo()
