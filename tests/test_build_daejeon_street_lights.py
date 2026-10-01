"""data/daejeon_street_lights.json 자체 검사.

실행: python -m tests.test_build_daejeon_street_lights
"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_street_lights.json"


def _load():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_all_five_districts_present_not_empty():
    data = _load()
    assert len(data) > 1000, "전체 186만건 중 일부만 스캔하고 '대전 없다'고 잘못 결론내는 걸 막는 회귀 테스트"
    districts = {r["district"] for r in data}
    assert districts == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_coordinates_are_real_floats():
    data = _load()
    for r in data[:200]:
        lat, lon = float(r["latitude"]), float(r["longitude"])
        assert 36.0 < lat < 36.6, "대전 위도 범위를 벗어남"
        assert 127.2 < lon < 127.6, "대전 경도 범위를 벗어남"


def test_seogu_has_most_matching_density_table():
    data = _load()
    from collections import Counter
    counts = Counter(r["district"] for r in data)
    assert counts["서구"] == max(counts.values()), "daejeon_district_density.json 기준 최고밀도 구와 일치해야 함"


if __name__ == "__main__":
    test_all_five_districts_present_not_empty()
    test_coordinates_are_real_floats()
    test_seogu_has_most_matching_density_table()
    print("OK")
