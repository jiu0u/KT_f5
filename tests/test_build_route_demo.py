"""scripts/build_route_demo.py 자체 검사.

실행: python -m tests.test_build_route_demo
"""
from scripts.build_route_demo import ROUTE_BUFFER_M, build
from src.accident_risk import candidates_along_route, point_to_segment_distance_m


def test_all_matches_within_buffer():
    result = build()
    assert result["matched_count"] > 0, "데모 경로 근처에 후보가 하나도 없으면 활용 레이어를 보여줄 수 없다"
    assert all(c["dist_to_route_m"] <= ROUTE_BUFFER_M for c in result["matches"])


def test_matches_sorted_by_distance():
    result = build()
    dists = [c["dist_to_route_m"] for c in result["matches"]]
    assert dists == sorted(dists)


def test_point_on_segment_has_zero_distance():
    d = point_to_segment_distance_m(36.35, 127.45, 36.35, 127.45, 36.36, 127.46)
    assert d < 1.0


def test_point_far_from_route_is_excluded():
    route = [(36.3494310, 127.4377711), (36.3471713, 127.4565957)]
    far_point = [{"lat": 36.20, "lon": 127.10}]  # 경로에서 수십km 떨어진 지점
    assert candidates_along_route(route, far_point, 150.0) == []


if __name__ == "__main__":
    test_all_matches_within_buffer()
    test_matches_sorted_by_distance()
    test_point_on_segment_has_zero_distance()
    test_point_far_from_route_is_excluded()
    print("OK")
