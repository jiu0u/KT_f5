"""물질별로 "확인된 폐기물 공급 후보"와 "취급은 하지만 배출 증거 없는 후보"를 나눈다.

CLAUDE.md 2단계(AI 후보탐색) 원칙: 최종판정이 아니라 검토할 후보를 좁히는 역할만 한다.
여기서 나누는 두 그룹도 마찬가지다.

- 폐기물이동량(pyegi_kg) > 0인 사업장 → confirmed_supplier: 그 물질을 실제로 폐기물로
  내보낸 증거가 있음. 순환경제 매칭의 "공급 후보".
- 같은 물질을 취급하지만 폐기물이동량 0인 사업장 → other_handler: 원료로 쓰거나 생산만
  하고 폐기물로는 안 내보냈을 수 있음. "수요 검토 후보"이지, 실제 수요가 있다는 뜻은
  아니다 — PRTR은 원료 부족량을 조사하지 않으므로 이후 직접 확인이 필요하다.

물질별로 공급 후보가 최소 1곳 있고 다른 취급 사업장이 최소 1곳 더 있을 때만 후보쌍으로
출력한다(공급자만 있거나 취급자만 있으면 매칭할 상대가 없으므로 제외).

실행: python -m scripts.find_matching_candidates
"""
import json
from collections import defaultdict
from pathlib import Path

SRC_PATH = Path(__file__).parent.parent / "data" / "waste_registry_ncis.json"
OUT_PATH = Path(__file__).parent.parent / "data" / "matching_candidates_ncis.json"


def main():
    records = json.loads(SRC_PATH.read_text(encoding="utf-8"))

    by_cas: dict[str, dict] = defaultdict(lambda: {"substance": "", "confirmed_suppliers": [], "other_handlers": []})
    for r in records:
        bucket = by_cas[r["cas_no"]]
        bucket["substance"] = r["components"][0]
        entry = {"company": r["company"], "address": r["address"], "industry": r["industry"],
                 "amount_ton_per_year": r["amount_ton_per_year"]}
        if r["confirmed_waste"]:
            bucket["confirmed_suppliers"].append(entry)
        else:
            bucket["other_handlers"].append(entry)

    candidates = []
    for cas_no, bucket in by_cas.items():
        if bucket["confirmed_suppliers"] and (len(bucket["confirmed_suppliers"]) + len(bucket["other_handlers"])) > 1:
            candidates.append({"cas_no": cas_no, **bucket})

    OUT_PATH.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"매칭 후보가 있는 물질: {len(candidates)}종 -> {OUT_PATH}")
    for c in candidates:
        print(f"  {c['substance']}({c['cas_no']}): 공급 후보 {len(c['confirmed_suppliers'])}곳, "
              f"기타 취급 {len(c['other_handlers'])}곳")


if __name__ == "__main__":
    main()
