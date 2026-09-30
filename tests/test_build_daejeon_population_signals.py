"""대전 인구 신호 결과 자체 점검 -- 행안부 실데이터가 실제 지역 특성과 맞는지 확인.
실행: python -m tests.test_build_daejeon_population_signals
"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_population_signals.json"


def _load() -> dict[str, dict]:
    return {r["district"]: r for r in json.loads(DATA_PATH.read_text(encoding="utf-8"))}


def test_all_five_districts_present():
    data = _load()
    assert set(data) == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_yuseong_has_highest_youth_ratio():
    # 유성구는 KAIST·충남대 밀집 대학가 -- 청년 1인가구 비중이 대전에서 가장 높아야 실데이터로서 말이 됨
    data = _load()
    youth_ratios = {d: r["youth_one_person_household_ratio"] for d, r in data.items()}
    assert max(youth_ratios, key=youth_ratios.get) == "유성구"


def test_ratios_are_valid_proportions():
    data = _load()
    for r in data.values():
        assert 0 <= r["one_person_household_ratio"] <= 1
        assert 0 <= r["youth_one_person_household_ratio"] <= 1
        assert 0 <= r["elderly_one_person_household_ratio"] <= 1


def demo():
    test_all_five_districts_present()
    test_yuseong_has_highest_youth_ratio()
    test_ratios_are_valid_proportions()
    print("OK - 대전 인구 신호 자체 점검 통과 (유성구 청년1인가구 비중 최고치로 실데이터 검증)")


if __name__ == "__main__":
    demo()
