"""2단계 · AI 후보탐색 (MVP).

ponytail: 실제 한국어 문장임베딩(ko-sroberta 등, CLAUDE.md 3.1단계 참고) 대신
의존성 없는 CAS No. 완전일치 + word-overlap 유사도로 시작. 후보 텍스트가 길고
다양해져 이 방식으로 변별력이 떨어지면 sentence-transformers 임베딩 + cosine
similarity(FAISS)로 교체.
"""
from .schema import WasteRecord


def _tokenize(text: str) -> set[str]:
    return set(text.replace(",", " ").split())


def _text_similarity(a: WasteRecord, b: WasteRecord) -> float:
    tokens_a = _tokenize(a.description) | set(a.components)
    tokens_b = _tokenize(b.description) | set(b.components)
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(overlap) / len(union)


def score(a: WasteRecord, b: WasteRecord) -> float:
    """CAS No.가 둘 다 있고 일치하면 최고점(1.0), 아니면 텍스트 유사도로 대체."""
    if a.cas_no and b.cas_no and a.cas_no == b.cas_no:
        return 1.0
    return _text_similarity(a, b)


def find_candidates(
    target: WasteRecord, pool: list[WasteRecord], top_k: int = 5
) -> list[tuple[WasteRecord, float]]:
    """target과 매칭 가능성이 높은 후보를 유사도 순 top_k개로 반환 (자기 자신 제외).

    3단계(화학·법적 검증)는 별도 룰베이스 모듈에서 처리 — 여기서는 최종판정을
    내리지 않고 검토할 후보를 좁히는 역할만 한다 (CLAUDE.md 3.2단계 원칙).
    """
    scored = [
        (candidate, score(target, candidate))
        for candidate in pool
        if candidate.id != target.id
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]
