"""matching_candidates_ncis.json의 물질 전부(19종)에 대해 scripts.demo.analyze()를
돌려 결과를 한 파일로 모은다. 캠프 발표자료·아티팩트에 그대로 쓸 수 있는 형태.

실행: python -m scripts.generate_report
"""
import json
from pathlib import Path

from scripts.demo import analyze

DATA_DIR = Path(__file__).parent.parent / "data"
CANDIDATES_PATH = DATA_DIR / "matching_candidates_ncis.json"
OUT_PATH = DATA_DIR / "full_matching_report.json"


def main():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    results = [analyze(c["cas_no"]) for c in candidates]
    results = [r for r in results if r]  # analyze()가 None을 반환할 일은 없지만 방어적으로

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    with_legal_hit = sum(
        1 for r in results if any(c["legal_verdict"] == "가능성있음" for c in r["ranked_candidates"])
    )
    print(f"물질 {len(results)}종 분석 완료 -> {OUT_PATH}")
    print(f"3단계에서 '가능성있음' 후보가 하나라도 나온 물질: {with_legal_hit}종")


if __name__ == "__main__":
    main()
