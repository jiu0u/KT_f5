"""빈집 후보 생성 자체 점검. 실행: python -m tests.test_build_vacant_house_candidates"""
from scripts.build_vacant_house_candidates import DONGGU_REAL_COUNTS, REAL_CASES, build


def test_donggu_counts_match_real_source_table():
    result = build()
    donggu = [h for h in result if h["district"] == "동구" and not h["is_real_case"]]
    expected_total = sum(sum(counts) for counts in DONGGU_REAL_COUNTS.values())
    assert len(donggu) == expected_total == 385, "동구는 실측 표와 정확히 같은 개수여야 함"


def test_real_cases_flagged_and_located_correctly():
    result = build()
    real = [h for h in result if h["is_real_case"]]
    assert len(real) == len(REAL_CASES) == 5
    assert all(h["is_simulated"] for h in real), "실제 사례도 건물 속성은 합성값이라 is_simulated=True여야 함"
    locations = {(h["district"], h["dong"]) for h in real}
    assert locations == {(d, dong) for d, dong, _ in REAL_CASES}


def demo():
    test_donggu_counts_match_real_source_table()
    test_real_cases_flagged_and_located_correctly()
    print("OK - 빈집 후보 생성 자체 점검 통과")


if __name__ == "__main__":
    demo()
