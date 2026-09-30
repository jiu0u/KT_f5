"""빈집 후보 생성 자체 점검. 실행: python -m tests.test_build_vacant_house_candidates"""
from scripts.build_vacant_house_candidates import REAL_CASES, REAL_GRADE_COUNTS, build


def test_each_district_matches_its_real_source_table():
    result = build()
    for district, dong_counts in REAL_GRADE_COUNTS.items():
        houses = [h for h in result if h["district"] == district and not h["is_real_case"]]
        expected_total = sum(sum(counts) for counts in dong_counts.values())
        assert len(houses) == expected_total, f"{district}는 실측 표와 정확히 같은 개수여야 함"


def test_total_matches_three_districts_combined():
    result = build()
    non_real_case = [h for h in result if not h["is_real_case"]]
    assert len(non_real_case) == 385 + 310 + 464, "동구+서구+대덕구 실측 합계(2026 기준)"


def test_real_cases_flagged_and_located_correctly():
    result = build()
    real = [h for h in result if h["is_real_case"]]
    assert len(real) == len(REAL_CASES) == 5
    assert all(h["is_simulated"] for h in real), "실제 사례도 건물 속성은 합성값이라 is_simulated=True여야 함"
    locations = {(h["district"], h["dong"]) for h in real}
    assert locations == {(d, dong) for d, dong, _ in REAL_CASES}


def demo():
    test_each_district_matches_its_real_source_table()
    test_total_matches_three_districts_combined()
    test_real_cases_flagged_and_located_correctly()
    print("OK - 빈집 후보 생성 자체 점검 통과 (동구·서구·대덕구 3개 구 실측 + 실제 사례 5곳)")


if __name__ == "__main__":
    demo()
