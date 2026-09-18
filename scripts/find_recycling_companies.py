"""matching_candidates_ncis.json 안에서 업종이 '폐기물 수집,운반,처리 및 원료재생업'인
기업만 골라내는 스크립트. 이 기업들은 배출기업이 아니라 이미 폐기물을 처리/재생하는
'재활용업체' 그 자체 -- A안(재활용업체 대상 리드매칭)의 실제 수요자 후보다.
실행: python -m scripts.find_recycling_companies
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SRC_PATH = DATA_DIR / "matching_candidates_ncis.json"
OUT_PATH = DATA_DIR / "recycling_companies_daejeon.json"


def find_recycling_companies() -> list[dict]:
    data = json.loads(SRC_PATH.read_text(encoding="utf-8"))
    recyclers: dict[str, dict] = {}

    for entry in data:
        cas_no = entry["cas_no"]
        substance = entry["substance"]
        for role in ("confirmed_suppliers", "other_handlers"):
            for c in entry.get(role, []):
                if "폐기물" not in c.get("industry", ""):
                    continue
                key = c["company"]
                if key not in recyclers:
                    recyclers[key] = {
                        "company": key,
                        "address": c["address"],
                        "industry": c["industry"],
                        "handled_substances": [],
                    }
                recyclers[key]["handled_substances"].append(
                    {
                        "cas_no": cas_no,
                        "substance": substance,
                        "role": role,  # confirmed_suppliers: 실제 폐기물이동량>0 확인됨 / other_handlers: 취급만 확인
                        "amount_ton_per_year": c.get("amount_ton_per_year"),
                    }
                )

    return sorted(recyclers.values(), key=lambda r: -len(r["handled_substances"]))


def build() -> list[dict]:
    result = find_recycling_companies()
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def demo():
    result = build()
    assert len(result) >= 1, "재활용업체가 최소 1곳은 나와야 함"
    assert all(r["handled_substances"] for r in result)
    top = result[0]
    assert top["company"] == "(주)동양환경"
    assert len(top["handled_substances"]) >= 6
    print(f"OK - 재활용업체 {len(result)}곳 발견, data/recycling_companies_daejeon.json 저장")


if __name__ == "__main__":
    demo()
