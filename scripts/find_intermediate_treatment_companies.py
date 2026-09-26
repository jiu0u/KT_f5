"""waste_registry_daedeok.json 안에서 처리방법이 '중간처분'(소각/중화/파쇄 등)인
수탁업체만 골라내는 스크립트. '재활용업체'(원료가 필요한 곳)와 달리 '중간처분업체'는
폐기물 자체를 처리(주로 소각)하는 곳 -- 동양환경 인터뷰로 재활용업체 가정이 깨진 뒤
타겟을 중간처분업체로 넓히기 위한 후보 목록.
대덕구 데이터에만 handlers/methods(수탁업체별 처리방법)가 들어있어 대덕구로 범위 한정.
실행: python -m scripts.find_intermediate_treatment_companies
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SRC_PATH = DATA_DIR / "waste_registry_daedeok.json"
OUT_PATH = DATA_DIR / "intermediate_treatment_companies_daedeok.json"


def find_intermediate_treatment_companies() -> list[dict]:
    data = json.loads(SRC_PATH.read_text(encoding="utf-8"))
    companies: dict[str, dict] = {}

    for entry in data:
        handlers = entry.get("handlers") or []
        methods = entry.get("methods") or []
        for handler, method in zip(handlers, methods):
            if not method.startswith("중간처분"):
                continue
            if handler not in companies:
                companies[handler] = {"company": handler, "handled_waste": []}
            companies[handler]["handled_waste"].append(
                {
                    "method": method,
                    "waste_type": entry.get("waste_type", ""),
                    "components": entry.get("components", []),
                    "generator": entry.get("company", ""),
                }
            )

    return sorted(companies.values(), key=lambda c: -len(c["handled_waste"]))


def build() -> list[dict]:
    result = find_intermediate_treatment_companies()
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def demo():
    result = build()
    assert len(result) >= 1, "중간처분업체가 최소 1곳은 나와야 함"
    assert all(c["handled_waste"] for c in result)
    print(f"OK - 중간처분업체 {len(result)}곳 발견, data/intermediate_treatment_companies_daedeok.json 저장")


if __name__ == "__main__":
    demo()
