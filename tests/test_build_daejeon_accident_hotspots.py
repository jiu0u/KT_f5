"""대전 사고다발지역 결과 자체 점검 -- "저밀도 지역은 사고 기록 자체가 적다"는
핵심 전제를 실데이터로 확인한다. 실행: python -m tests.test_build_daejeon_accident_hotspots
"""
import json
import re
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_accident_hotspots.json"


def _load() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_all_five_districts_present():
    data = _load()
    assert {r["district"] for r in data} == {"동구", "중구", "서구", "유성구", "대덕구"}


def _dong_of(location_name: str) -> str:
    m = re.search(r"구\s*(\S+?동)", location_name)
    return m.group(1) if m else "미상"


def test_sannae_dong_has_zero_recorded_hotspots_despite_being_a_real_dong():
    # 산내동(동구 최저밀도·빈집 최다 동)이 사고다발지역에 단 한 건도 안 잡힘 --
    # "저밀도=기록 부족"이라는 피벗의 핵심 전제를 실데이터로 확인하는 사례
    data = _load()
    donggu_dongs = Counter(_dong_of(r["acdntAreaLcNm"]) for r in data if r["district"] == "동구")
    assert donggu_dongs.get("산내동", 0) == 0
    assert sum(donggu_dongs.values()) > 50, "동구 자체는 사고다발지역이 충분히 많아야 함(비교 기준)"


def test_seogu_has_most_hotspots_matching_highest_density():
    # 서구는 밀도도 최고(daejeon_district_density.json), 사고다발지역 수도 최다여야 자연스러움
    data = _load()
    counts = Counter(r["district"] for r in data)
    assert max(counts, key=counts.get) == "서구"


def demo():
    test_all_five_districts_present()
    test_sannae_dong_has_zero_recorded_hotspots_despite_being_a_real_dong()
    test_seogu_has_most_hotspots_matching_highest_density()
    print("OK - 대전 사고다발지역 자체 점검 통과 (산내동 사고기록 0건으로 핵심 전제 실증)")


if __name__ == "__main__":
    demo()
