"""기업 DB에서 화학물질취급정보(CAS No. 15종)와 겹치는 회사를 찾는다.

product/industry 텍스트에 물질명이 부분 문자열로 나오면 후보로 잡는다. 이 회사들은
해당 화학물질을 실제로 생산·취급할 가능성이 있어, 인근 사업장의 동일 폐기물(예: 폐황산)
재활용 수요처 후보로 쓸 수 있다 — CLAUDE.md 2단계(AI 후보탐색) 원칙과 동일하게, 여기서도
최종판정이 아니라 검토할 후보를 좁히는 역할만 한다.

실행: python -m scripts.find_chemical_companies
"""
import json
from pathlib import Path

from scripts.load_yuseong_waste import load_cas_lookup

DATA_DIR = Path(__file__).parent.parent / "data"
COMPANY_DB = DATA_DIR / "company_db.json"
OUT_PATH = DATA_DIR / "chemical_candidate_companies.json"


def main():
    cas_lookup = load_cas_lookup()
    companies = json.loads(COMPANY_DB.read_text(encoding="utf-8"))

    hits = []
    for company in companies:
        text = f"{company.get('product', '')} {company.get('industry', '')}"
        for substance, cas_no in cas_lookup.items():
            if substance and substance in text:
                hits.append({
                    "company": company["name"],
                    "address": company.get("address", ""),
                    "district": company.get("district", ""),
                    "matched_substance": substance,
                    "cas_no": cas_no,
                    "product": company.get("product", ""),
                    "industry": company.get("industry", ""),
                })

    OUT_PATH.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"화학물질 취급 후보: {len(hits)}건 -> {OUT_PATH}")
    for h in hits:
        print(f"  - {h['company']} ({h['matched_substance']}, CAS {h['cas_no']})")


if __name__ == "__main__":
    main()
