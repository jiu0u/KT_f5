"""대덕특구(042) 이전가능기술 추출 결과 자체 점검. 실행: python -m tests.test_find_daedeok_tech_transfer"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daedeok_tech_transfer_candidates.json"


def _load() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_all_entries_are_daejeon_area_code():
    records = _load()
    assert len(records) >= 10000, "2023~2026 기간만으로도 만 건 이상 나와야 함(실측 15,080건)"
    assert all(r["devPhone"].startswith("042") for r in records)


def test_known_daedeok_institutes_present():
    records = _load()
    org_names = {r["orgName"] for r in records}
    known = {"한국화학연구원", "한국전자통신연구원", "한국기계연구원", "한국원자력연구원"}
    assert known.issubset(org_names), "대덕특구 주요 출연연이 전부 잡혀야 함"


def demo():
    test_all_entries_are_daejeon_area_code()
    test_known_daedeok_institutes_present()
    print("OK - 대덕특구 이전가능기술 추출 자체 점검 통과")


if __name__ == "__main__":
    demo()
