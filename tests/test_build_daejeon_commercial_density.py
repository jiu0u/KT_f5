"""대전 상권밀도(상가업소 수) 결과 자체 점검. 실행: python -m tests.test_build_daejeon_commercial_density"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_commercial_density.json"


def _load() -> dict[str, int]:
    return {r["district"]: r["store_count"] for r in json.loads(DATA_PATH.read_text(encoding="utf-8"))}


def test_all_five_districts_present():
    assert set(_load()) == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_seogu_has_most_stores_daedeok_has_fewest():
    # 서구는 대전에서 인구·상업지구가 가장 큰 구, 대덕구는 산업단지 위주라 상가가 가장 적음
    counts = _load()
    assert max(counts, key=counts.get) == "서구"
    assert min(counts, key=counts.get) == "대덕구"


def demo():
    test_all_five_districts_present()
    test_seogu_has_most_stores_daedeok_has_fewest()
    print("OK - 대전 상권밀도 자체 점검 통과 (서구 최다/대덕구 최소로 실데이터 검증)")


if __name__ == "__main__":
    demo()
