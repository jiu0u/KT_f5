"""대전 횡단보도 결과 자체 점검. 실행: python -m tests.test_build_daejeon_crosswalks"""
import json
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_crosswalks.json"


def _load() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_all_five_districts_present():
    data = _load()
    assert {r["signguNm"] for r in data} == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_yuseong_has_most_crosswalks_matching_area_and_road_network():
    # 유성구는 대전에서 면적이 가장 넓고(177km²) 도로망도 넓게 퍼져있어 횡단보도 수가 가장 많음
    data = _load()
    counts = Counter(r["signguNm"] for r in data)
    assert max(counts, key=counts.get) == "유성구"


def test_total_count_is_substantial():
    assert len(_load()) > 5000


def demo():
    test_all_five_districts_present()
    test_yuseong_has_most_crosswalks_matching_area_and_road_network()
    test_total_count_is_substantial()
    print("OK - 대전 횡단보도 자체 점검 통과 (유성구 최다로 실데이터 검증)")


if __name__ == "__main__":
    demo()
