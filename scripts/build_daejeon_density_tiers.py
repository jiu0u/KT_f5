"""대전 5개 구의 인구밀도를 계산해 저밀도/고밀도로 나눈다 -- "저밀도 지역 특화"
교통사고 위험지점 예측의 핵심 전제(표본이 적은 지역을 먼저 식별)를 위한 기초 신호.

면적은 위키백과 대전광역시 행정구역 문서 기준 공식 수치(국토교통부 통계 출처),
인구는 scripts/build_daejeon_population_signals.py 결과를 재사용 -- 새 API 없이
이미 있는 데이터만으로 구별 밀도를 계산할 수 있다.

⚠ 한계: 구 단위 밀도라서 동구(산내동 등 산간지역 포함)처럼 한 구 안에 도심과
외곽이 섞여 있으면 왜곡된다 -- 동구가 구 전체로는 밀도 최하위지만, 동구 안에서도
중앙동·효동 같은 원도심은 실제로는 밀도가 높을 것이다. 동 단위 면적 데이터를
구하면 바로 교체할 지점.

실행: python -m scripts.build_daejeon_density_tiers
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
POPULATION_PATH = DATA_DIR / "daejeon_population_signals.json"
OUT_PATH = DATA_DIR / "daejeon_district_density.json"

# 대전광역시 행정구역 면적(km²) -- 위키백과 "대전광역시의 행정 구역" 문서, 국토교통부 통계 기준
AREA_KM2 = {
    "동구": 136.63, "중구": 62.13, "서구": 95.48, "유성구": 177.27, "대덕구": 68.46,
}

LOW_DENSITY_THRESHOLD = 2500  # 명/km², 대전 5개구 중앙값 부근 -- 임의 기준치(검증 안 됨)


def build() -> list[dict]:
    population = {r["district"]: r["total_population"] for r in json.loads(POPULATION_PATH.read_text(encoding="utf-8"))}
    result = []
    for district, area in AREA_KM2.items():
        pop = population[district]
        density = round(pop / area, 1)
        result.append({
            "district": district, "population": pop, "area_km2": area,
            "density_per_km2": density, "is_low_density": density < LOW_DENSITY_THRESHOLD,
        })
    result.sort(key=lambda r: r["density_per_km2"])
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    for r in result:
        tag = "저밀도" if r["is_low_density"] else "고밀도"
        print(f"{r['district']}: {r['density_per_km2']:,}명/km² ({tag})")
    print(f"완료 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
