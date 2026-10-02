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


# 산내동은 행정동이고 사고·신호등 데이터는 법정동 이름으로 적혀 있다(행정동 "산내동" 문자열로
# 찾으면 0건이 나오는 착시 -- 처음에 이걸로 "산내동 사고기록 0건"이라고 잘못 보고했었다).
# 관할 법정동 10곳: 동구청 "행정동 및 법정동 안내" 기준.
SANNAE_LEGAL_DONGS = ["낭월동", "대별동", "이사동", "대성동", "장척동", "소호동", "구도동", "삼괴동", "상소동", "하소동"]


def test_sannae_hotspots_are_about_a_tenth_of_rest_of_donggu_per_traffic_light():
    # 산내동(동구 최저밀도·빈집 최다 동)은 사고다발지역이 2건뿐 -- 신호등 100개당 건수가
    # 동구 나머지 지역의 약 1/10. "0건"이 아니라 "극단적으로 적다"가 정확한 사실이다.
    hotspots = [r for r in _load() if r["district"] == "동구"]
    lights = json.loads((DATA_PATH.parent / "daejeon_traffic_lights.json").read_text(encoding="utf-8"))
    lights = [r for r in lights if r["signguNm"] == "동구"]

    def in_sannae(text: str) -> bool:
        return any(d in (text or "") for d in SANNAE_LEGAL_DONGS)

    sn_hot = sum(1 for r in hotspots if in_sannae(r["acdntAreaLcNm"]))
    sn_light = sum(1 for r in lights if in_sannae(r.get("lnmadr") or r.get("rdnmadr")))
    rest_hot, rest_light = len(hotspots) - sn_hot, len(lights) - sn_light

    assert sn_hot == 2, "낭월동·대성동 각 1건"
    assert sn_light > 500, "산내동에도 신호등은 충분히 있다(모델이 볼 수 있는 지점)"
    assert (sn_hot / sn_light) < 0.2 * (rest_hot / rest_light)


def test_seogu_has_most_hotspots_matching_highest_density():
    # 서구는 밀도도 최고(daejeon_district_density.json), 사고다발지역 수도 최다여야 자연스러움
    data = _load()
    counts = Counter(r["district"] for r in data)
    assert max(counts, key=counts.get) == "서구"


def demo():
    test_all_five_districts_present()
    test_sannae_hotspots_are_about_a_tenth_of_rest_of_donggu_per_traffic_light()
    test_seogu_has_most_hotspots_matching_highest_density()
    print("OK - 대전 사고다발지역 자체 점검 통과 (산내동은 신호등 100개당 사고다발지역이 동구 나머지의 약 1/10)")


if __name__ == "__main__":
    demo()
