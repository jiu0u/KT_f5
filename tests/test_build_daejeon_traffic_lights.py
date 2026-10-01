"""대전 신호등 결과 자체 점검 -- 처음에 "대전 데이터 없음"으로 잘못 결론 냈던
전력이 있어서, 이 결과가 비어있지 않다는 것 자체를 테스트로 고정해 둔다.
실행: python -m tests.test_build_daejeon_traffic_lights
"""
import json
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_traffic_lights.json"


def _load() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_all_five_districts_present_not_empty():
    # 부분 페이지네이션만 보고 "대전 신호등 데이터가 없다"고 오판했던 사례 -- 전수 조회로 뒤집힘
    data = _load()
    assert len(data) > 1000, "전국 99페이지를 다 돌아야 나오는 수치라 작으면 다시 부분조회로 잘못됐을 가능성"
    assert {r["signguNm"] for r in data} == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_yuseong_has_most_traffic_lights():
    data = _load()
    counts = Counter(r["signguNm"] for r in data)
    assert max(counts, key=counts.get) == "유성구"


def demo():
    test_all_five_districts_present_not_empty()
    test_yuseong_has_most_traffic_lights()
    print("OK - 대전 신호등 자체 점검 통과 (전수조회로 데이터 존재 확인)")


if __name__ == "__main__":
    demo()
