"""End-to-End 데모: 물질 하나를 골라 1~5단계 파이프라인을 실제로 돌려본다.

CLAUDE.md 5단계 파이프라인 중 지금까지 실데이터로 채운 건 1~2단계(정보구조화 +
AI 후보탐색, data/waste_registry_ncis.json)뿐이었다. 이 데모는 거기서 멈추지 않고
3~5단계를 "지금 있는 real data로 할 수 있는 만큼" 이어붙여서 전체 흐름을 보여준다.

⚠ 정직하게 밝히는 한계:
- 3단계(화학·법적 검증): 폐기물관리법 별표5의3·위험물안전관리법 별표19의 실제 룰
  엔진은 아직 없다. 여기서는 그 자리에 "수동 확인 필요" 표시만 남긴다 — 없는 룰을
  있는 것처럼 판정하지 않는다.
- 4단계(경제성·물류): 실제 지오코딩(카카오맵/네이버 API) 없이, 주소의 구(區)가
  같은지만 보는 근접도 프록시를 쓴다. ponytail: naive 근접도 프록시, 실제 좌표
  기반 거리 계산으로 교체 가능(카카오맵 API 키 확보 시).
- 5단계(TOPSIS): 기준이 근접도·사업장 규모(종업원 수) 두 가지뿐이라 가중치는
  동일(0.5/0.5)로 둔 placeholder. 실제 화학적합성·법적리스크 점수가 생기면 기준을
  늘려야 한다.

실행: python -m scripts.demo [--cas 007664-93-9]
"""
import argparse
import json
import math
from pathlib import Path

from scripts.build_company_db import infer_district

DATA_DIR = Path(__file__).parent.parent / "data"
CANDIDATES_PATH = DATA_DIR / "matching_candidates_ncis.json"
ENTRPS_DETAIL_PATH = DATA_DIR / "ncis_entrps_detail_daejeon_2024.json"

DEFAULT_CAS = "007664-93-9"  # 황산


def load_employee_lookup() -> dict[str, int]:
    detail = json.loads(ENTRPS_DETAIL_PATH.read_text(encoding="utf-8"))
    lookup = {}
    for r in detail:
        try:
            lookup[r["name"]] = int(r["employees"])
        except (ValueError, TypeError):
            lookup[r["name"]] = 0
    return lookup


def infer_proximity(address_a: str, address_b: str) -> float:
    """근접도 프록시: 같은 구(區)면 1.0, 아니면 0.5. 실제 거리 아님."""
    da, db = infer_district(address_a), infer_district(address_b)
    return 1.0 if da and da == db else 0.5


def topsis(alternatives: list[dict], criteria: list[str], weights: list[float]) -> list[tuple[dict, float]]:
    """단순 TOPSIS. 기준은 전부 '높을수록 좋음'으로 가정(vector 정규화)."""
    n = len(alternatives)
    norms = {c: math.sqrt(sum(a[c] ** 2 for a in alternatives)) or 1.0 for c in criteria}
    weighted = [
        {c: (a[c] / norms[c]) * w for c, w in zip(criteria, weights)}
        for a in alternatives
    ]
    ideal_best = {c: max(row[c] for row in weighted) for c in criteria}
    ideal_worst = {c: min(row[c] for row in weighted) for c in criteria}

    scores = []
    for i in range(n):
        dist_best = math.sqrt(sum((weighted[i][c] - ideal_best[c]) ** 2 for c in criteria))
        dist_worst = math.sqrt(sum((weighted[i][c] - ideal_worst[c]) ** 2 for c in criteria))
        closeness = dist_worst / (dist_best + dist_worst) if (dist_best + dist_worst) else 0.0
        scores.append((alternatives[i], closeness))
    return sorted(scores, key=lambda pair: pair[1], reverse=True)


def run(cas_no: str):
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    entry = next((c for c in candidates if c["cas_no"] == cas_no), None)
    if entry is None:
        print(f"'{cas_no}'에 대한 매칭 후보가 없습니다. data/matching_candidates_ncis.json 확인.")
        return

    print(f"=== {entry['substance']} (CAS {cas_no}) 순환경제 매칭 데모 ===\n")

    print("[1~2단계] 정보구조화 + AI 후보탐색 (실데이터: NCIS PRTR 2024, 대전)")
    suppliers = entry["confirmed_suppliers"]
    print(f"  확인된 폐기물 공급 후보: {len(suppliers)}곳")
    for s in suppliers:
        print(f"    - {s['company']} ({s['industry']}) 폐기물이동량 {s['amount_ton_per_year']}톤/년")
    print(f"  기타 취급 후보(수요 검토 대상): {len(entry['other_handlers'])}곳\n")

    print("[3단계] 화학·법적 검증")
    print("  [!] 폐기물관리법 별표5의3 / 위험물안전관리법 별표19 룰 엔진 미구현")
    print("  [!] 아래 후보는 전부 '검토 필요' 상태이며, 법적 적합 여부를 판정한 것이 아님\n")

    employees = load_employee_lookup()
    supplier = suppliers[0]
    print(f"[4~5단계] 경제성·물류 근접도 + TOPSIS (기준: 근접도, 사업장 규모)")
    alternatives = []
    for h in entry["other_handlers"]:
        alternatives.append({
            **h,
            "proximity": infer_proximity(supplier["address"], h["address"]),
            "scale": float(employees.get(h["company"], 0)),
        })
    if not alternatives:
        print("  기타 취급 후보가 없어 순위를 매길 수 없음")
        return

    ranked = topsis(alternatives, ["proximity", "scale"], [0.5, 0.5])

    print(f"  공급 후보: {supplier['company']} ({supplier['address']})\n")
    print(f"  {'순위':<4}{'기업':<26}{'구':<8}{'종업원수':>8}{'근접도':>8}{'종합점수':>10}")
    for rank, (cand, score) in enumerate(ranked, start=1):
        district = infer_district(cand["address"]) or "-"
        print(f"  {rank:<4}{cand['company']:<26}{district:<8}{int(cand['scale']):>8}{cand['proximity']:>8.1f}{score:>10.3f}")

    print(f"\n  1위 추천: {ranked[0][0]['company']} - 화학적합성·법적기준은 별도 확인 필요")


def main():
    parser = argparse.ArgumentParser(description="순환경제 매칭 End-to-End 데모")
    parser.add_argument("--cas", default=DEFAULT_CAS, help="CAS No. (기본값: 황산 007664-93-9)")
    args = parser.parse_args()
    run(args.cas)


if __name__ == "__main__":
    main()
