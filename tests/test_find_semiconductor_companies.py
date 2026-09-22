"""반도체 관련 기업 추출 자체 점검. 실행: python -m tests.test_find_semiconductor_companies"""
from scripts.find_semiconductor_companies import find_semiconductor_companies


def test_confirmed_chemical_companies_come_first():
    result = find_semiconductor_companies()
    names = [r["name"] for r in result]
    assert "주식회사 켐옵틱스" in names
    assert result[0]["confirmed_chemicals"], "정렬 후 맨 앞은 실제 물질이 확인된 기업이어야 함"


def test_all_entries_are_semiconductor_related():
    result = find_semiconductor_companies()
    kws = ["반도체", "전자부품", "전자 부품", "웨이퍼", "소자"]
    for r in result:
        text = (r["industry"] or "") + (r["product"] or "")
        assert any(kw in text for kw in kws)


def demo():
    test_confirmed_chemical_companies_come_first()
    test_all_entries_are_semiconductor_related()
    print("OK - 반도체 관련 기업 추출 자체 점검 통과")


if __name__ == "__main__":
    demo()
