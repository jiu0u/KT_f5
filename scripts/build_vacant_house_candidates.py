"""빈집 후보 데이터 생성 -- 위치·등급은 실제 공개자료/보도 기준, 건물 속성(면적·층수·
노후연수)은 합성값이다. src/vacant_house.py의 설계 근거 참고.

1) 동구 385건 + 서구 254건 + 대덕구 379건: 각 구 data.go.kr 빈집현황 페이지의
   행정동×등급 표(미리보기) 그대로 사용 -- 행정동·등급별 개수는 실제, 개별
   건물 속성만 합성.
2) 실제 사례 5곳: 2026년 대전형 빈집정비사업 확정 대상지(언론보도, 2026-04-23
   공유재산 심의 완료) -- 동구 용운동·용전동, 중구 부사동, 서구 도마동, 대덕구 읍내동.
   위치는 실제, 건물 속성은 뉴스에 없어 합성.

⚠ 유성구·중구는 아직 못 넣었다: 유성구는 921건 개별기록이 있지만 2021년 1회성
스냅샷이라 등급·연령 정보가 없고, 중구는 행정동×등급 census 자체가 없이
"빈집정비사업 추진현황"(연도별 철거실적)만 공개돼 있어 이 스키마에 안 맞는다.
그래서 중구는 위 실제 사례(부사동) 1곳으로만 대표된다.

⚠ 대덕구 원본 데이터 품질 문제: "합계" 컬럼이 16개 행정동 중 4곳(신탄진동·
석봉동·덕암동·목상동)에서 0으로 나오는데 1~3등급 컬럼엔 값이 있다(예: 신탄진동
합계 0인데 1등급 24 + 2등급 30 + 3등급 2). 원본 CSV 자체의 오류로 보고 등급별
컬럼 합만 신뢰해서 썼다.

실행: python -m scripts.build_vacant_house_candidates
"""
import json
import random
from pathlib import Path

from src.vacant_house import VacantHouse

OUT_PATH = Path(__file__).parent.parent / "data" / "vacant_house_candidates.json"
RANDOM_SEED = 42

# 각 구 data.go.kr 빈집현황 페이지 미리보기 표: 행정동 -> (1등급,2등급,3등급[,4등급]) 개수
REAL_GRADE_COUNTS: dict[str, dict[str, tuple[int, ...]]] = {
    "동구": {  # 대전광역시 동구_빈집현황_20260720 (4등급 컬럼 있으나 전 행정동 0)
        "중앙동": (3, 12, 3, 0), "신인동": (12, 11, 3, 0), "효동": (10, 17, 3, 0),
        "판암1동": (8, 16, 3, 0), "판암2동": (0, 1, 2, 0), "용운동": (9, 11, 3, 0),
        "대동": (6, 16, 5, 0), "자양동": (19, 7, 1, 0), "가양1동": (12, 8, 1, 0),
        "가양2동": (18, 5, 0, 0), "용전동": (16, 12, 0, 0), "성남동": (5, 12, 2, 0),
        "홍도동": (12, 4, 0, 0), "삼성동": (9, 12, 1, 0), "대청동": (3, 20, 8, 0),
        "산내동": (17, 18, 9, 0),
    },
    "서구": {  # 대전광역시 서구_행정동별 빈집현황_20241205
        "도마동": (54, 30, 3), "복수동": (27, 9, 0), "변동": (23, 10, 1),
        "괴정동": (12, 14, 0), "원정동": (6, 10, 1), "탄방동": (9, 5, 0),
        "용문동": (4, 7, 1), "내동": (9, 2, 0), "정림동": (8, 3, 0),
        "갈마동": (6, 3, 0), "가수원동": (3, 6, 0), "봉곡동": (0, 6, 1),
        "평촌동": (0, 6, 1), "흑석동": (0, 5, 1), "가장동": (3, 1, 0),
        "괴곡동": (1, 2, 0), "산직동": (0, 2, 1), "장안동": (1, 2, 0),
        "월평동": (0, 3, 0), "용촌동": (0, 1, 1), "오동": (0, 0, 2),
        "매노동": (1, 0, 0), "관저동": (1, 0, 0), "도안동": (0, 1, 0),
        "우명동": (0, 0, 1),
    },
    "대덕구": {  # 대전광역시 대덕구_빈집현황_20260326 -- "합계" 컬럼 무시, 1~3등급 컬럼만 사용(위 경고 참고)
        "오정동": (34, 18, 2), "대화동": (84, 63, 8), "회덕동": (45, 51, 3),
        "비래동": (16, 1, 0), "송촌동": (13, 0, 0), "중리동": (9, 0, 0),
        "법1동": (0, 1, 0), "법2동": (0, 0, 0), "신탄진동": (24, 30, 2),
        "석봉동": (3, 5, 0), "덕암동": (38, 12, 0), "목상동": (0, 2, 0),
    },
}

# 2026년 대전형 빈집정비사업 확정 대상지 (언론보도, 2026-04-23 공유재산 심의 완료)
REAL_CASES = [
    ("동구", "용운동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("동구", "용전동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("중구", "부사동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("서구", "도마동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("대덕구", "읍내동", "대전시 2026년 빈집정비사업 확정 대상지"),
]

BUILDING_TYPES = ["단독주택(다가구)", "공동주택(다세대·연립)", "그 외 주택"]
BUILDING_TYPE_WEIGHTS = [0.55, 0.30, 0.15]  # ponytail: 국가 통계상 노후 빈집은 단독주택 비중이 높다는 일반 경향만 반영한 가정치


def _synthesize_attrs(rng: random.Random, grade: int) -> dict:
    building_type = rng.choices(BUILDING_TYPES, BUILDING_TYPE_WEIGHTS)[0]
    floors = 1 if building_type != "공동주택(다세대·연립)" else rng.randint(2, 4)
    area_m2 = round(rng.uniform(45, 90) if building_type == "단독주택(다가구)" else rng.uniform(35, 70), 1)
    # 등급이 높을수록(노후·철거 대상) 노후연수도 크게 -- 등급 체계와 방향만 맞춘 단순 매핑
    age_years = rng.randint(20, 35) + (grade - 1) * 10
    return {"building_type": building_type, "floors": floors, "area_m2": area_m2, "age_years": age_years}


def build_district_candidates(rng: random.Random, district: str, dong_counts: dict[str, tuple[int, ...]]) -> list[VacantHouse]:
    houses = []
    for dong, counts in dong_counts.items():
        for grade, count in enumerate(counts, start=1):
            for i in range(count):
                attrs = _synthesize_attrs(rng, grade)
                houses.append(VacantHouse(
                    id=f"{district}-{dong}-{grade}-{i+1}",
                    district=district, dong=dong, condition_grade=grade,
                    is_real_case=False, is_simulated=True,
                    source_note=f"위치·등급: data.go.kr 대전광역시 {district}_빈집현황 실측 / 건물속성: 합성",
                    **attrs,
                ))
    return houses


def build_real_case_candidates(rng: random.Random) -> list[VacantHouse]:
    houses = []
    for i, (district, dong, note) in enumerate(REAL_CASES, start=1):
        attrs = _synthesize_attrs(rng, grade=3)  # 정비사업 확정 대상 = 철거·정비급이므로 3등급으로 취급
        houses.append(VacantHouse(
            id=f"realcase-{i}", district=district, dong=dong, condition_grade=3,
            is_real_case=True, is_simulated=True,
            source_note=f"위치: {note} (실제) / 면적·층수·노후연수: 보도자료에 없어 합성",
            **attrs,
        ))
    return houses


def build() -> list[dict]:
    rng = random.Random(RANDOM_SEED)
    houses = []
    for district, dong_counts in REAL_GRADE_COUNTS.items():
        houses += build_district_candidates(rng, district, dong_counts)
    houses += build_real_case_candidates(rng)
    result = [vars(h) for h in houses]
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    real_cases = sum(1 for h in result if h["is_real_case"])
    per_district = {}
    for h in result:
        if not h["is_real_case"]:
            per_district[h["district"]] = per_district.get(h["district"], 0) + 1
    breakdown = ", ".join(f"{d} {n}건" for d, n in per_district.items())
    print(f"완료 - 빈집 후보 {len(result)}건({breakdown} + 실제 사례 {real_cases}건) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
