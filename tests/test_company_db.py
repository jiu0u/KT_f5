"""기업 DB 병합 + 화학물질 후보탐색 자체 점검. 실행: python -m tests.test_company_db"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def test_company_db_merged_and_deduped():
    companies = json.loads((DATA_DIR / "company_db.json").read_text(encoding="utf-8"))
    assert len(companies) > 300, "PDF 목표(300개 이상)를 넘어야 함"
    multi_source = [c for c in companies if len(c["sources"]) > 1]
    assert multi_source, "대덕구 대기배출업소·제조업공장등록 사이에 겹치는 기업이 있어야 함"


def test_chemical_candidates_have_valid_cas():
    hits = json.loads((DATA_DIR / "chemical_candidate_companies.json").read_text(encoding="utf-8"))
    assert hits, "화학물질 후보가 최소 1건은 있어야 함"
    for h in hits:
        assert h["cas_no"]
        assert h["matched_substance"] in f"{h['product']} {h['industry']}"


def demo():
    test_company_db_merged_and_deduped()
    test_chemical_candidates_have_valid_cas()
    print("OK - 기업 DB 병합 + 화학물질 후보탐색 자체 점검 통과")


if __name__ == "__main__":
    demo()
