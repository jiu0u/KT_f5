"""대덕구 대기배출업소·제조업공장등록 + 유성구 폐기물배출자 → 통합 기업 DB.

PDF 제안서의 "기업 300개 이상의 데이터베이스(기업명·주소·업종·배출 폐기물 종류)" 목표에 대응.
같은 기업이 여러 원본에 나오면 이름 기준(법인 표기 ㈜/(주)/(유) 등만 제거하고 나머지는
그대로 비교 — 지점명까지 다르면 별개 사업장으로 취급)으로 병합해 industry/product/
waste_types/sources를 합친다.

실행: python -m scripts.build_company_db
"""
import csv
import io
import json
from pathlib import Path

from src.company import CompanyRecord

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR = Path(__file__).parent.parent / "data"
AIR_CSV = RAW_DIR / "대전광역시 대덕구_대기배출업소현황_20250904.csv"
FACTORY_CSV = RAW_DIR / "대전광역시 대덕구_제조업공장등록현황_20260623.csv"
YUSEONG_JSON = DATA_DIR / "waste_registry_yuseong.json"
OUT_PATH = DATA_DIR / "company_db.json"

CORP_MARKERS = ["㈜", "(주)", "(유)", "(사)", "(재)", "(사단법인)", "(재단법인)", "(합)"]


def normalize(name: str) -> str:
    for marker in CORP_MARKERS:
        name = name.replace(marker, "")
    return " ".join(name.split())


def read_csv_rows(path: Path, encoding: str) -> list[dict]:
    text = path.read_bytes().decode(encoding)
    return list(csv.DictReader(io.StringIO(text)))


class CompanyDB:
    def __init__(self):
        self._by_key: dict[str, CompanyRecord] = {}

    def add(self, name: str, address: str = "", district: str = "", industry: str = "",
            product: str = "", waste_types: list[str] | None = None, source: str = ""):
        name = name.strip()
        if not name:
            return
        key = normalize(name)
        record = self._by_key.get(key)
        if record is None:
            record = CompanyRecord(id=f"co-{len(self._by_key) + 1}", name=name)
            self._by_key[key] = record
        if not record.address and address:
            record.address = address
        if not record.district and district:
            record.district = district
        if not record.industry and industry:
            record.industry = industry
        if not record.product and product:
            record.product = product
        for w in waste_types or []:
            if w not in record.waste_types:
                record.waste_types.append(w)
        if source and source not in record.sources:
            record.sources.append(source)

    def records(self) -> list[CompanyRecord]:
        return list(self._by_key.values())


def build() -> CompanyDB:
    db = CompanyDB()

    for row in read_csv_rows(AIR_CSV, "utf-8-sig"):
        db.add(
            name=row["상호명"], address=row["도로명주소"], district="대덕구",
            industry=row["업종명"], source="daedeok_air",
        )

    for row in read_csv_rows(FACTORY_CSV, "cp949"):
        db.add(
            name=row["업체명"], address=row["공장대표주소(도로명)"], district="대덕구",
            product=row["주생산품"], source="daedeok_factory",
        )

    yuseong = json.loads(YUSEONG_JSON.read_text(encoding="utf-8"))
    for r in yuseong:
        db.add(
            name=r["company"], address=r["address"], district="유성구",
            waste_types=r["components"], source="yuseong_waste",
        )

    return db


def main():
    db = build()
    records = db.records()
    OUT_PATH.write_text(
        json.dumps([r.__dict__ for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    from collections import Counter
    source_counts = Counter(s for r in records for s in r.sources)
    multi_source = sum(1 for r in records if len(r.sources) > 1)
    print(f"기업 DB: {len(records)}건(중복 제거 후) -> {OUT_PATH}")
    print(f"출처별 건수: {dict(source_counts)}")
    print(f"2개 이상 출처에 겹치는 기업: {multi_source}건")


if __name__ == "__main__":
    main()
