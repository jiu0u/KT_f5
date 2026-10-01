"""교통사고 위험지점 예측 — 공간 조인 + 간이 위험도 추정 뼈대.

방법(요약): 고밀도 구(표본 충분)에서 "교차로 주변 조건(횡단보도 수·도로폭)과
실제 사고다발지역 근접 여부"의 관계를 집계로 배우고, 그 관계를 저밀도 구의
신호등 지점(아직 사고다발지역으로 안 잡힌 곳)에 적용해 "조건은 비슷한데
기록이 없는" 후보를 찾는다. 머신러닝 모델이 아니라 구간별 집계(버킷) 비율이다
-- ponytail: 표본이 수백 건뿐이라 정식 모델을 학습할 근거가 안 됨, 집계가 솔직하다.

⚠ 한계:
- "사고다발지역 반경 150m 이내"를 그 지점이 이미 사고다발로 "확인된" 것으로
  취급한다. 150m는 도로교통공단이 사고다발지역을 묶을 때 쓰는 기준 반경과
  같은 값을 가져온 것뿐, 신호등-사고지점 간 실제 인과 반경을 검증한 건 아니다.
- 격자(그리드) 기반 최근접 탐색을 쓴다 -- 정밀한 GIS 라이브러리 없이 좌표를
  약 110m 간격 격자로 반올림해 인접 칸만 비교하는 방식. 격자 경계에 걸친
  지점은 누락될 수 있다(허용 가능한 근사로 판단).
- 고밀도 구의 표본(서구 104건, 중구 80건)도 통계적으로 크지 않다 -- 버킷을
  세분화할수록(도로폭 구간 더 쪼개기 등) 표본이 더 희박해져 추정이 불안정해진다.
- **도로폭(roadBt)이 대전 데이터에서 전부 "0"(플레이스홀더)이라 실질적으로
  못 쓴다** — 그래서 지금 위험도 추정은 사실상 "횡단보도 밀집도" 한 가지
  차원으로만 갈린다(scripts/build_daejeon_road_signs.py 한계 참고). 애초에
  5개 신호(신호등 유무, 도로폭, 조명, 시간대, 인구밀도, 대중교통접근성) 중
  "도로폭"은 데이터 품질 문제로 탈락, "조명"은 전국 표준데이터 자체를 못
  찾았고, "시간대별"은 이 표준데이터셋에 발생 시각 필드가 없고, "대중교통접근성"은
  아직 안 붙였다 — 처음 구상한 6개 신호 중 실질적으로 쓰는 건 인구밀도(저밀도
  판정)와 횡단보도뿐이다.
"""
import json
import math
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
HOTSPOT_RADIUS_M = 150.0  # 도로교통공단 사고다발지역 선정 기준 반경과 동일
GRID_DEG = 0.001  # 위도 기준 약 111m -- 탐색 반경(150m) 안쪽 격자 크기


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class GridIndex:
    """좌표를 격자 칸에 담아 반경 내 후보만 빠르게 추려주는 간이 공간 인덱스."""

    def __init__(self, points: list[dict]):
        self.points = points
        self.cells: dict[tuple[int, int], list[dict]] = {}
        for p in points:
            key = self._cell_key(p["lat"], p["lon"])
            self.cells.setdefault(key, []).append(p)

    @staticmethod
    def _cell_key(lat: float, lon: float) -> tuple[int, int]:
        return (round(lat / GRID_DEG), round(lon / GRID_DEG))

    def nearby(self, lat: float, lon: float) -> list[dict]:
        cx, cy = self._cell_key(lat, lon)
        result = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                result += self.cells.get((cx + dx, cy + dy), [])
        return result

    def nearest_distance_m(self, lat: float, lon: float) -> float | None:
        candidates = self.nearby(lat, lon)
        if not candidates:
            return None
        return min(haversine_m(lat, lon, p["lat"], p["lon"]) for p in candidates)

    def count_within(self, lat: float, lon: float, radius_m: float) -> int:
        return sum(1 for p in self.nearby(lat, lon) if haversine_m(lat, lon, p["lat"], p["lon"]) <= radius_m)


def _to_point(lat: str, lon: str, **extra) -> dict | None:
    try:
        return {"lat": float(lat), "lon": float(lon), **extra}
    except (TypeError, ValueError):
        return None


def load_accident_points() -> list[dict]:
    rows = json.loads((DATA_DIR / "daejeon_accident_hotspots.json").read_text(encoding="utf-8"))
    return [p for r in rows if (p := _to_point(r["latitude"], r["longitude"], district=r["district"]))]


def load_traffic_light_points() -> list[dict]:
    rows = json.loads((DATA_DIR / "daejeon_traffic_lights.json").read_text(encoding="utf-8"))
    return [p for r in rows if (p := _to_point(r["latitude"], r["longitude"], district=r["signguNm"], address=r.get("lnmadr") or r.get("rdnmadr")))]


def load_crosswalk_points() -> list[dict]:
    rows = json.loads((DATA_DIR / "daejeon_crosswalks.json").read_text(encoding="utf-8"))
    return [p for r in rows if (p := _to_point(r["latitude"], r["longitude"]))]


def load_road_sign_points() -> list[dict]:
    rows = json.loads((DATA_DIR / "daejeon_road_signs.json").read_text(encoding="utf-8"))
    points = []
    for r in rows:
        try:
            width = float(r["roadBt"])
        except (TypeError, ValueError):
            continue
        p = _to_point(r["latitude"], r["longitude"], width_m=width)
        if p:
            points.append(p)
    return points


def load_low_density_districts() -> set[str]:
    rows = json.loads((DATA_DIR / "daejeon_district_density.json").read_text(encoding="utf-8"))
    return {r["district"] for r in rows if r["is_low_density"]}


def point_to_segment_distance_m(lat: float, lon: float, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """점-선분 최단거리(m). 평면(등거리원통) 근사 -- 수백m~수km 구간 경로에선
    오차가 무시할 수준이라 GIS 라이브러리 없이 이 정도로 충분하다고 판단."""
    lat0 = math.radians((lat1 + lat2) / 2)
    mx, my = 111320.0 * math.cos(lat0), 111320.0

    def to_xy(la, lo):
        return (lo - lon1) * mx, (la - lat1) * my

    px, py = to_xy(lat, lon)
    bx, by = to_xy(lat2, lon2)
    if bx == 0 and by == 0:
        return haversine_m(lat, lon, lat1, lon1)
    t = max(0.0, min(1.0, (px * bx + py * by) / (bx * bx + by * by)))
    cx, cy = t * bx, t * by
    return math.hypot(px - cx, py - cy)


def candidates_along_route(route_points: list[tuple[float, float]], points: list[dict], buffer_m: float) -> list[dict]:
    """경로(위경도 점들을 이은 직선 구간들) 주변 buffer_m 안의 지점만 추려
    "이 경로에서 거리별 위험도" 를 보여주기 위한 함수. 경로는 실제 도로를 따라가지
    않는 직선 근사다 -- 도로망 데이터·길찾기 API가 없어서 그대로 쓸 수 없다는
    한계를 그대로 안고 간다(목업 단계에서는 개념 증명이 목적)."""
    segments = list(zip(route_points, route_points[1:]))
    result = []
    for p in points:
        min_dist = min(
            point_to_segment_distance_m(p["lat"], p["lon"], lat1, lon1, lat2, lon2)
            for (lat1, lon1), (lat2, lon2) in segments
        )
        if min_dist <= buffer_m:
            result.append({**p, "dist_to_route_m": round(min_dist, 1)})
    return result
