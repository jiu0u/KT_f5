"""빈집 활용 추천 End-to-End 데모.

⚠ 정직하게 밝히는 한계 (src/vacant_house_match.py 참고):
- 9개 판단기준 중 `전략산업인접도` 하나만 실 데이터(반도체 관련 기업 구별 분포)다.
  나머지 8개(인구구조, 유동인구, 상권, 생활SOC, 주차장, 교통)는 아직 못 붙여서
  전부 미확보 — 그래서 모든 추천에 coverage(용도별 가중치 중 실제로 채워진 비율)를
  같이 찍는다. coverage가 낮을수록 "지금은 못 믿을 추천"이라는 뜻.
- 빈집의 위치(구·동)는 실측/실제 사례지만 면적·층수·노후연수는 합성값이다
  (scripts/build_vacant_house_candidates.py).
- 용도별 가중치 자체도 도메인 검증 없이 상식선에서 잡은 추정치.

실행: python -m scripts.demo_vacant_house [--house-id realcase-5]
"""
import argparse
import json
from pathlib import Path

from src.vacant_house_match import build_location_signals, recommend_top3

DATA_DIR = Path(__file__).parent.parent / "data"
CANDIDATES_PATH = DATA_DIR / "vacant_house_candidates.json"
DEFAULT_HOUSE_ID = "realcase-5"  # 대덕구 읍내동 - 전략산업인접도가 가장 뚜렷하게 갈리는 실제 사례


def run(house_id: str):
    houses = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    house = next((h for h in houses if h["id"] == house_id), None)
    if house is None:
        print(f"'{house_id}' 후보를 찾을 수 없습니다. data/vacant_house_candidates.json 확인.")
        return

    print(f"=== 빈집 활용 추천 데모: {house['id']} ({house['district']} {house['dong']}) ===\n")
    label = "실제 사례" if house["is_real_case"] else "합성 후보"
    print(f"[위치] {label} — {house['source_note']}")
    print(f"[건물속성(합성)] {house['building_type']}, {house['floors']}층, {house['area_m2']}㎡, 준공 후 {house['age_years']}년, {house['condition_grade']}등급\n")

    signals = build_location_signals(house["district"], house["dong"])
    print("[판단기준 확보 현황]")
    for c, v in sorted(signals.criteria.items()):
        print(f"  - {c}: {'미확보' if v is None else round(v, 3)}")

    top3 = recommend_top3(signals)
    print(f"\n[추천 Top {len(top3)}] (coverage = 이 용도 가중치 중 실제 데이터로 채워진 비율)")
    if not top3:
        print("  판단 가능한 용도 없음 — 모든 용도의 필요 신호가 전부 미확보")
        return
    for rank, r in enumerate(top3, start=1):
        print(f"  {rank}위 {r.use_type}: 점수 {r.score:.3f} (coverage {r.coverage:.0%}, 반영기준 {r.used_criteria}, 미반영 {r.missing_criteria})")

    print("\n  ⚠ coverage가 100%가 아닌 한 이 순위는 참고용일 뿐 실제 추천으로 못 씀 — 위 '한계' 문단 참고")


def main():
    parser = argparse.ArgumentParser(description="빈집 활용 추천 데모")
    parser.add_argument("--house-id", default=DEFAULT_HOUSE_ID, help="data/vacant_house_candidates.json의 id")
    args = parser.parse_args()
    run(args.house_id)


if __name__ == "__main__":
    main()
