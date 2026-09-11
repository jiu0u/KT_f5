"""NCIS PRTR 물질별×사업장 데이터를 WasteRecord 스키마로 변환.

data/ncis_prtr_daejeon_2024.json은 (물질, 사업장) 쌍의 나열이다. WasteRecord.cas_no는
문자열 하나뿐이라 회사 단위로 묶어버리면(여러 물질 취급 시) 대표 CAS 하나만 남아 나머지
물질의 매칭이 깨진다 — 그래서 여기선 회사 단위로 합치지 않고 (물질, 사업장) 쌍 하나당
레코드 하나를 그대로 만든다. 한 회사가 여러 물질을 취급하면 레코드도 여러 개 생기는데,
전체 취급 물질 목록은 data/company_db.json의 chemicals 필드에서 따로 확인할 수 있다.

주의: PRTR은 "이 사업장이 이 물질을 취급/배출한다"는 사실만 알려줄 뿐 그 물질이
폐기물인지 원료인지는 구분하지 않는다 — 같은 물질을 취급하는 두 사업장이 나오면
그건 순환경제 매칭의 "후보"이지 확정된 폐기물→원료 관계는 아니다(3~4단계 검증 필요).

실행: python -m scripts.build_ncis_waste_registry
"""
import json
from pathlib import Path

SRC_PATH = Path(__file__).parent.parent / "data" / "ncis_prtr_daejeon_2024.json"
OUT_PATH = Path(__file__).parent.parent / "data" / "waste_registry_ncis.json"


def main():
    substances = json.loads(SRC_PATH.read_text(encoding="utf-8"))

    records = []
    for s in substances:
        for c in s["companies"]:
            records.append({
                "id": f"ncis-{len(records) + 1}",
                "company": c["name"],
                "address": c["address"],
                "industry": c["industry"],
                "waste_type": "",
                "cas_no": s["cas_no"],
                "components": [s["substance"]],
                "state": "",
                "amount_ton_per_year": 0.0,
                "description": f"PRTR 2024 등록 취급물질: {s['substance']}",
            })

    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    unique_companies = len({r["company"] for r in records})
    print(f"(물질,사업장) 레코드: {len(records)}건, 사업장 중복제거 {unique_companies}개 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
