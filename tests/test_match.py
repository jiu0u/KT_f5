"""최소 자체 점검. 실행: python -m tests.test_match"""
import json
from pathlib import Path

from src.match import find_candidates
from src.schema import WasteRecord


def _load_sample() -> list[WasteRecord]:
    path = Path(__file__).parent.parent / "data" / "sample_waste.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    return [WasteRecord(**r) for r in records]


def test_cas_no_exact_match_ranks_first():
    pool = _load_sample()
    target = next(r for r in pool if r.id == "w1")
    results = find_candidates(target, pool)
    assert results, "후보가 있어야 함"
    top_candidate, top_score = results[0]
    assert top_score == 1.0, f"CAS No. 일치 후보가 1위여야 함, got {top_score}"
    assert top_candidate.cas_no == target.cas_no


def test_text_similarity_matches_related_description():
    pool = _load_sample()
    target = next(r for r in pool if r.id == "w3")  # 폐수산화나트륨 배출
    results = find_candidates(target, pool)
    top_candidate, top_score = results[0]
    assert top_candidate.id == "w4", "수산화나트륨 원료 수요 기업이 최상위 후보여야 함"
    assert top_score > 0.0


def test_no_self_match():
    pool = _load_sample()
    target = pool[0]
    results = find_candidates(target, pool)
    assert all(candidate.id != target.id for candidate, _ in results)


def demo():
    test_cas_no_exact_match_ranks_first()
    test_text_similarity_matches_related_description()
    test_no_self_match()
    print("OK - 1~2단계(구조화 + 후보탐색) MVP 자체 점검 통과")


if __name__ == "__main__":
    demo()
