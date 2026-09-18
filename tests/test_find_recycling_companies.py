"""재활용업체 추출 자체 점검. 실행: python -m tests.test_find_recycling_companies"""
from scripts.find_recycling_companies import find_recycling_companies


def test_dongyang_hwangyeong_is_top_recycler():
    result = find_recycling_companies()
    names = [r["company"] for r in result]
    assert "(주)동양환경" in names
    dongyang = next(r for r in result if r["company"] == "(주)동양환경")
    assert dongyang["industry"] == "폐기물 수집, 운반, 처리 및 원료 재생업"
    handled_cas = {s["cas_no"] for s in dongyang["handled_substances"]}
    assert "000067-63-0" in handled_cas  # IPA(2-프로판올) 포함 확인


def test_all_entries_are_waste_industry():
    result = find_recycling_companies()
    assert all("폐기물" in r["industry"] for r in result)


def demo():
    test_dongyang_hwangyeong_is_top_recycler()
    test_all_entries_are_waste_industry()
    print("OK - 재활용업체 추출 자체 점검 통과")


if __name__ == "__main__":
    demo()
