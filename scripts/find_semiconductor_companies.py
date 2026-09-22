"""company_db.json에서 업종/주생산품이 반도체 관련인 기업만 골라내는 스크립트.
NCIS로 실제 화학물질/폐기물이 확인된 기업과, 업종상 반도체 관련이지만 아직
폐기물 데이터가 없는 기업을 나눠서 저장한다 -- 대전 반도체 폐기물 배출기업
컨택 대상 풀을 넓히는 용도.
실행: python -m scripts.find_semiconductor_companies
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SRC_PATH = DATA_DIR / "company_db.json"
OUT_PATH = DATA_DIR / "semiconductor_companies_daejeon.json"

KEYWORDS = ["반도체", "전자부품", "전자 부품", "웨이퍼", "소자"]


def find_semiconductor_companies() -> list[dict]:
    db = json.loads(SRC_PATH.read_text(encoding="utf-8"))
    hits = []
    for c in db:
        text = (c.get("industry", "") or "") + (c.get("product", "") or "")
        if not any(kw in text for kw in KEYWORDS):
            continue
        hits.append(
            {
                "name": c["name"],
                "district": c.get("district"),
                "address": c.get("address"),
                "industry": c.get("industry"),
                "product": c.get("product"),
                "confirmed_chemicals": [
                    ch.get("substance") for ch in c.get("chemicals", [])
                ],
            }
        )
    # 실제 폐기물 데이터(confirmed_chemicals)가 있는 기업을 앞으로
    hits.sort(key=lambda c: (-len(c["confirmed_chemicals"]), c["name"]))
    return hits


def build() -> list[dict]:
    result = find_semiconductor_companies()
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def demo():
    result = build()
    assert len(result) >= 30, "반도체 관련 기업이 최소 30곳은 나와야 함"
    confirmed = [c for c in result if c["confirmed_chemicals"]]
    assert len(confirmed) >= 1
    assert result[0]["confirmed_chemicals"], "확인된 물질이 있는 기업이 맨 앞에 와야 함"
    print(
        f"OK - 반도체 관련 기업 {len(result)}곳 (실물질확인 {len(confirmed)}곳), "
        "data/semiconductor_companies_daejeon.json 저장"
    )


if __name__ == "__main__":
    demo()
