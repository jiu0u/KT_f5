"""대전 주차장 공급량 결과 자체 점검. 실행: python -m tests.test_build_daejeon_parking_supply"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_parking_supply.json"


def _load() -> dict[str, dict]:
    return {r["district"]: r for r in json.loads(DATA_PATH.read_text(encoding="utf-8"))}


def test_all_five_districts_present():
    assert set(_load()) == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_jungu_has_most_capacity_daedeok_has_least():
    # 중구는 대전역·원도심 공영주차장이 몰려있고, 대덕구는 산업단지 위주라 주차면수가 가장 적음
    data = _load()
    capacities = {d: r["capacity"] for d, r in data.items()}
    assert max(capacities, key=capacities.get) == "중구"
    assert min(capacities, key=capacities.get) == "대덕구"


def test_capacity_and_lot_count_are_positive():
    for r in _load().values():
        assert r["lot_count"] > 0
        assert r["capacity"] > 0


def demo():
    test_all_five_districts_present()
    test_jungu_has_most_capacity_daedeok_has_least()
    test_capacity_and_lot_count_are_positive()
    print("OK - 대전 주차장 공급량 자체 점검 통과 (중구 최다/대덕구 최소로 실데이터 검증)")


if __name__ == "__main__":
    demo()
