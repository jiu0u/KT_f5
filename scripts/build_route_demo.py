"""예측 모델을 "활용하는" 레이어 데모 -- 위험지점을 또 예측하는 게 아니라,
이미 뽑아놓은 예측 위험후보(accident_risk_candidates.json)를 보행 경로 위에
얹어서 "이 경로를 지나면 몇 군데를 지나가게 되는가"를 보여준다.

KOROAD 위험도로예보시스템도 이미 위험도를 계산해서 도로관리기관에 제공하지만,
그 결과를 보행자가 실제로 쓰는 경로추천/알림 형태로 내려주는 마지막 단계는
없다 -- 이 스크립트는 그 "활용" 단계를 아주 작게 보여주는 개념증명이다.

경로는 실제 길찾기 API 없이 동구 가양동의 실제 신호등 두 지점(서쪽 끝 교차로 →
동쪽 끝 교차로, 약 1.7km)을 직선으로 이은 것이다 -- 실제 도로를 따라가는 경로가
아니라는 한계를 README에도 명시한다.

실행: python -m scripts.build_route_demo
"""
import json
from pathlib import Path

from src.accident_risk import candidates_along_route

OUT_PATH = Path(__file__).parent.parent / "data" / "route_demo_result.json"
DATA_DIR = Path(__file__).parent.parent / "data"

ROUTE_BUFFER_M = 150.0  # HOTSPOT_RADIUS_M과 동일 기준 사용
DEMO_ROUTE = {
    "label": "동구 가양동 보행경로 예시 (서쪽 교차로 -> 동쪽 교차로, 직선 근사)",
    "points": [
        (36.3494310, 127.4377711),  # 가양동 636 인근 교차로
        (36.3471713, 127.4565957),  # 가양동 683 인근 교차로
    ],
}


def build() -> dict:
    candidates = json.loads((DATA_DIR / "accident_risk_candidates.json").read_text(encoding="utf-8"))
    reliable = [c for c in candidates if c["rate_reliable"]]
    route_points = DEMO_ROUTE["points"]
    on_route = candidates_along_route(route_points, reliable, ROUTE_BUFFER_M)
    on_route.sort(key=lambda c: c["dist_to_route_m"])

    result = {
        "route_label": DEMO_ROUTE["label"],
        "route_points": route_points,
        "buffer_m": ROUTE_BUFFER_M,
        "matched_count": len(on_route),
        "matches": on_route,
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    print(f"경로: {result['route_label']}")
    print(f"경로 {result['buffer_m']}m 반경 안의 예측 위험후보: {result['matched_count']}건 (기존 길찾기 앱은 모르는 지점)")
    for c in result["matches"][:5]:
        print(f"  {c['address']} - 경로에서 {c['dist_to_route_m']}m, 추정위험률 {c['estimated_risk_rate']:.0%}")
    print(f"\n완료 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
