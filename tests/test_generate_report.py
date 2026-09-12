"""전체 물질 리포트 생성 자체 점검. 실행: python -m tests.test_generate_report"""
import json
from pathlib import Path

from scripts.demo import analyze

DATA_PATH = Path(__file__).parent.parent / "data" / "full_matching_report.json"


def test_report_covers_all_19_substances():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert len(data) == 19
    assert all(r["cas_no"] and r["substance"] for r in data)


def test_analyze_handles_no_other_handlers_without_crashing():
    # 자일렌: 공급 후보만 있고 기타 취급 후보가 0곳인 실제 케이스
    result = analyze("001330-20-7")
    assert result is not None
    assert result["other_handler_count"] == 0
    assert result["ranked_candidates"] == []
    assert result["top_pick"] is None


def test_analyze_unknown_cas_returns_none():
    assert analyze("000000-00-0") is None


def demo():
    test_report_covers_all_19_substances()
    test_analyze_handles_no_other_handlers_without_crashing()
    test_analyze_unknown_cas_returns_none()
    print("OK - 전체 리포트 생성 자체 점검 통과")


if __name__ == "__main__":
    demo()
