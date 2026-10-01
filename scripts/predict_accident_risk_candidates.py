"""교통사고 위험지점 예측 메인 로직 -- 고밀도 구에서 배운 "조건↔사고" 비율을
저밀도 구의 신호등 지점에 적용해, 사고 기록은 없지만 조건이 비슷한 후보를 뽑는다.

절차:
1. 모든 신호등 지점에 대해 (사고다발지역까지 거리, 100m 내 횡단보도 수, 가까운
   도로폭, 100m 내 보안등 수) 특징을 공간조인으로 계산한다.
2. 고밀도 구(서구·중구)에서, (도로폭구간, 횡단보도수구간, 보안등수구간) 조합별로
   실제 사고다발지역 150m 이내 비율을 집계한다 -- 이게 "학습된" 위험 비율표다.
3. 저밀도 구(동구·유성구·대덕구)의 신호등 중 사고다발지역에서 150m 넘게
   떨어진(=기록 없는) 지점에 같은 비율표를 적용해 추정 위험도를 매긴다.
4. 추정 위험도가 높은데 기록이 없는 지점을 "예측 위험지점 후보"로 출력한다.

⚠ src/accident_risk.py의 한계(150m 기준의 근거, 격자 근사, 표본 크기)가
그대로 적용된다. 버킷 표본이 작으면(`support`가 낮으면) 그 추정치는
우연일 가능성이 크다 -- 결과에 항상 같이 표시한다.

실행: python -m scripts.predict_accident_risk_candidates
"""
import json
from pathlib import Path

from src.accident_risk import (
    GridIndex,
    HOTSPOT_RADIUS_M,
    haversine_m,
    load_accident_points,
    load_crosswalk_points,
    load_low_density_districts,
    load_road_sign_points,
    load_street_light_points,
    load_traffic_light_points,
)

OUT_PATH = Path(__file__).parent.parent / "data" / "accident_risk_candidates.json"
HIGH_DENSITY_DISTRICTS = {"서구", "중구"}  # daejeon_district_density.json 기준 고밀도 2개 구
NEARBY_RADIUS_M = 100.0
MIN_SUPPORT = 5  # 이 밑으로 표본이 적은 버킷은 추정치를 신뢰 불가로 표시


def width_bucket(width_m: float | None) -> str:
    # 대전 도로안전표지의 roadBt는 전부 "0"(의미 없는 플레이스홀더)이라
    # 0 이하는 "6m미만"이 아니라 "정보없음"으로 처리한다 -- 아니면 모든 교차로가
    # 실제로는 데이터가 없을 뿐인데 "도로가 좁다"로 잘못 집계된다
    # (scripts/build_daejeon_road_signs.py 한계 참고).
    if width_m is None or width_m <= 0:
        return "도로폭정보없음"
    if width_m < 6:
        return "6m미만(좁음)"
    if width_m < 9:
        return "6~9m"
    return "9m이상"


def crosswalk_bucket(count: int) -> str:
    if count == 0:
        return "횡단보도0"
    if count == 1:
        return "횡단보도1"
    return "횡단보도2+"


def light_bucket(count: int) -> str:
    # 100m 반경 보안등 개수 -- 적을수록 야간 시야 확보가 안 되는 지점이라고 본다
    if count == 0:
        return "보안등0"
    if count <= 2:
        return "보안등1~2"
    return "보안등3+"


def build_features(lights: list[dict], accident_idx: GridIndex, crosswalk_idx: GridIndex, sign_idx: GridIndex, street_light_idx: GridIndex) -> list[dict]:
    rows = []
    for light in lights:
        dist = accident_idx.nearest_distance_m(light["lat"], light["lon"])
        is_known_hotspot = dist is not None and dist <= HOTSPOT_RADIUS_M

        nearby_signs = sign_idx.nearby(light["lat"], light["lon"])
        nearest_width = None
        if nearby_signs:
            closest = min(nearby_signs, key=lambda s: haversine_m(light["lat"], light["lon"], s["lat"], s["lon"]))
            if haversine_m(light["lat"], light["lon"], closest["lat"], closest["lon"]) <= NEARBY_RADIUS_M:
                nearest_width = closest["width_m"]

        crosswalk_count = crosswalk_idx.count_within(light["lat"], light["lon"], NEARBY_RADIUS_M)
        street_light_count = street_light_idx.count_within(light["lat"], light["lon"], NEARBY_RADIUS_M)

        rows.append({
            **light,
            "nearest_accident_m": round(dist, 1) if dist is not None else None,
            "is_known_hotspot": is_known_hotspot,
            "road_width_bucket": width_bucket(nearest_width),
            "crosswalk_bucket": crosswalk_bucket(crosswalk_count),
            "light_bucket": light_bucket(street_light_count),
        })
    return rows


def learn_risk_rates(high_density_rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    buckets: dict[tuple[str, str, str], list[bool]] = {}
    for r in high_density_rows:
        key = (r["road_width_bucket"], r["crosswalk_bucket"], r["light_bucket"])
        buckets.setdefault(key, []).append(r["is_known_hotspot"])

    rates = {}
    for key, labels in buckets.items():
        rates[key] = {
            "rate": sum(labels) / len(labels),
            "support": len(labels),
            "reliable": len(labels) >= MIN_SUPPORT,
        }
    return rates


def build() -> list[dict]:
    lights = load_traffic_light_points()
    accident_idx = GridIndex(load_accident_points())
    crosswalk_idx = GridIndex(load_crosswalk_points())
    sign_idx = GridIndex(load_road_sign_points())
    street_light_idx = GridIndex(load_street_light_points())
    low_density = load_low_density_districts()

    all_rows = build_features(lights, accident_idx, crosswalk_idx, sign_idx, street_light_idx)
    high_density_rows = [r for r in all_rows if r["district"] in HIGH_DENSITY_DISTRICTS]
    risk_rates = learn_risk_rates(high_density_rows)

    candidates = []
    for r in all_rows:
        if r["district"] not in low_density or r["is_known_hotspot"]:
            continue  # 저밀도 구이면서 아직 기록 없는 지점만 후보
        key = (r["road_width_bucket"], r["crosswalk_bucket"], r["light_bucket"])
        learned = risk_rates.get(key, {"rate": None, "support": 0, "reliable": False})
        candidates.append({**r, "estimated_risk_rate": learned["rate"], "rate_support": learned["support"], "rate_reliable": learned["reliable"]})

    candidates = [c for c in candidates if c["estimated_risk_rate"] is not None]
    candidates.sort(key=lambda c: -c["estimated_risk_rate"])
    OUT_PATH.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    return candidates


def main():
    candidates = build()
    reliable = [c for c in candidates if c["rate_reliable"]]
    print(f"저밀도 구 신호등 중 사고기록 없는 지점: {len(candidates)}건 (버킷 표본 {MIN_SUPPORT}+ 로 신뢰 가능: {len(reliable)}건)")
    print("\n[추정 위험도 상위 10곳 (표본 신뢰 가능한 것만)]")
    for c in reliable[:10]:
        print(f"  {c['district']} {c['address']} - 추정위험률 {c['estimated_risk_rate']:.0%} "
              f"(도로폭:{c['road_width_bucket']}, {c['crosswalk_bucket']}, {c['light_bucket']}, 버킷표본 {c['rate_support']}건)")
    print(f"\n완료 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
