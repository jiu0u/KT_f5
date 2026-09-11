"""유성구 실데이터 로더 자체 점검. 실행: python -m tests.test_load_yuseong"""
import json
from pathlib import Path

from src.match import find_candidates
from src.schema import WasteRecord

DATA_PATH = Path(__file__).parent.parent / "data" / "waste_registry_yuseong.json"
WASTE_RECORD_FIELDS = set(WasteRecord.__dataclass_fields__)


def _load() -> list[WasteRecord]:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [WasteRecord(**{k: v for k, v in r.items() if k in WASTE_RECORD_FIELDS}) for r in raw]


def test_130_real_companies_loaded():
    records = _load()
    assert len(records) == 130
    assert all(r.company and r.address for r in records)


def test_text_similarity_finds_a_real_candidate():
    records = _load()
    target = records[0]
    results = find_candidates(target, records)
    assert results, "실데이터에서도 후보가 나와야 함"
    # CAS No.가 이 데이터셋엔 없으므로(일반 폐기물 카테고리뿐) word-overlap 경로를 탐
    assert all(score < 1.0 for _, score in results), "CAS No. 완전일치는 이 데이터셋에 없음"


def demo():
    test_130_real_companies_loaded()
    test_text_similarity_finds_a_real_candidate()
    print("OK - 유성구 실데이터 로더 + 매칭 자체 점검 통과")


if __name__ == "__main__":
    demo()
