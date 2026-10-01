"""대전 구별 인구밀도 계산 자체 점검. 실행: python -m tests.test_build_daejeon_density_tiers"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_district_density.json"


def _load() -> dict[str, dict]:
    return {r["district"]: r for r in json.loads(DATA_PATH.read_text(encoding="utf-8"))}


def test_all_five_districts_present():
    assert set(_load()) == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_donggu_is_lowest_density_despite_being_old_downtown():
    # 동구는 산내동 등 산간지역을 포함해 면적이 커서, 원도심인데도 구 전체로는 밀도가 가장 낮음
    data = _load()
    densities = {d: r["density_per_km2"] for d, r in data.items()}
    assert min(densities, key=densities.get) == "동구"
    assert data["동구"]["is_low_density"] is True


def test_seogu_is_highest_density_and_not_low():
    data = _load()
    densities = {d: r["density_per_km2"] for d, r in data.items()}
    assert max(densities, key=densities.get) == "서구"
    assert data["서구"]["is_low_density"] is False


def demo():
    test_all_five_districts_present()
    test_donggu_is_lowest_density_despite_being_old_downtown()
    test_seogu_is_highest_density_and_not_low()
    print("OK - 대전 구별 밀도 계산 자체 점검 통과 (동구 최저밀도/서구 최고밀도 확인)")


if __name__ == "__main__":
    demo()
