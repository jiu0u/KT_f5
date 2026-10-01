"""대전 도로안전표지(도로폭) 결과 자체 점검. 실행: python -m tests.test_build_daejeon_road_signs"""
import json
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_road_signs.json"


def _load() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_all_five_districts_present():
    data = _load()
    assert {r["district"] for r in data} == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_road_width_is_fully_populated():
    data = _load()
    assert all((r.get("roadBt") or "").strip() for r in data), "도로폭이 빈 행이 있으면 안 됨(수집 시점엔 7221/7221 전부 있었음)"


def test_yuseong_has_most_signs():
    data = _load()
    counts = Counter(r["district"] for r in data)
    assert max(counts, key=counts.get) == "유성구"


def demo():
    test_all_five_districts_present()
    test_road_width_is_fully_populated()
    test_yuseong_has_most_signs()
    print("OK - 대전 도로안전표지 자체 점검 통과 (도로폭 100% 확보)")


if __name__ == "__main__":
    demo()
