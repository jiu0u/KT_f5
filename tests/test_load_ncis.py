"""NCIS PRTR 실데이터 로더 + CAS No. 실제 매칭 자체 점검. 실행: python -m tests.test_load_ncis"""
import json
from pathlib import Path

from src.match import find_candidates
from src.schema import WasteRecord

DATA_PATH = Path(__file__).parent.parent / "data" / "waste_registry_ncis.json"
WASTE_RECORD_FIELDS = set(WasteRecord.__dataclass_fields__)


def _load() -> list[WasteRecord]:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [WasteRecord(**{k: v for k, v in r.items() if k in WASTE_RECORD_FIELDS}) for r in raw]


def test_records_have_real_cas_no():
    records = _load()
    assert len(records) == 132, "(물질,사업장) 쌍 개수"
    assert len({r.company for r in records}) == 52, "중복제거한 사업장 수"
    assert all(r.cas_no for r in records), "PRTR 등록 레코드는 전부 CAS No.가 있어야 함"


def test_sulfuric_acid_companies_match_exactly():
    records = _load()
    sulfuric_acid_cas = "007664-93-9"
    targets = [r for r in records if r.cas_no == sulfuric_acid_cas]
    assert len(targets) >= 2, "황산을 취급하는 사업장이 대전에 여러 곳 있어야 함(실측 8곳)"

    results = find_candidates(targets[0], records)
    top_candidate, top_score = results[0]
    assert top_score == 1.0, "같은 CAS No.(황산)를 취급하는 다른 사업장이 1위로 나와야 함"
    assert top_candidate.cas_no == sulfuric_acid_cas


def demo():
    test_records_have_real_cas_no()
    test_sulfuric_acid_companies_match_exactly()
    print("OK - NCIS PRTR 실데이터 CAS No. 매칭 자체 점검 통과 (드디어 진짜 매칭 성공)")


if __name__ == "__main__":
    demo()
