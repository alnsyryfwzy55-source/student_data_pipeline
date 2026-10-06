import logging
import os
import time
from pathlib import Path

import pandas as pd

from app.sources.csv_source import extract_csv
from app.sources.api_source import extract_api
from app.sources.database_source import extract_database
from app.sources.mongodb_source import extract_mongodb, extract_mongodb_json
from app.sources.web_scraper_source import extract_web
from app.validation.quality import (
    validate_student_source, validate_api_source, validate_database_source,
    validate_mongodb_source, validate_web_source, split_final_data,
)
from app.transformation.cleaner import (
    clean_students, clean_api, clean_mongodb, clean_web,
)
from app.transformation.integration import integrate_data, add_derived_columns
from app.output.csv_writer import save_processed_data, save_rejected_data
from app.ml.prepare import save_ml_dataset
from app.utils.logger import setup_logger

BASE = Path(__file__).resolve().parent
logger = logging.getLogger("student_data_pipeline")


def extract_mongo_source(base: Path) -> pd.DataFrame:
    """Live MongoDB when MONGO_URI is set (fallback: local JSON export)."""
    fixture = base / "data/raw/mongodb_students.json"
    uri = os.getenv("MONGO_URI")
    if not uri:
        logger.info("MONGO_URI not set; using local MongoDB export")
        return extract_mongodb_json(fixture)
    try:
        return extract_mongodb(
            uri,
            os.getenv("MONGO_DATABASE", "student_pipeline"),
            os.getenv("MONGO_COLLECTION", "students"),
        )
    except Exception as exc:  # connection, auth, empty collection
        logger.warning("MongoDB extraction failed (%s); using local export", exc)
        return extract_mongodb_json(fixture)


def compatibility_rejections(sources: dict[str, pd.DataFrame],
                             already_rejected: set) -> pd.DataFrame:
    """Students present in some required sources but missing from others."""
    ids = {name: set(df["student_id"].dropna().astype(int))
           for name, df in sources.items()}
    rows = []
    for sid in sorted(set.union(*ids.values()) - already_rejected):
        missing = [name for name, found in ids.items() if sid not in found]
        if missing:
            rows.append({
                "student_id": sid,
                "source": "integration",
                "error_reason": "Incompatible student_id: missing in " + ", ".join(missing),
            })
    return pd.DataFrame(rows, columns=["student_id", "source", "error_reason"])


def run_pipeline(base: Path = BASE, out_base: Path | None = None):
    """Run the ETL. Inputs are read from `base`; outputs go to `out_base`."""
    out_base = Path(out_base) if out_base else Path(base)
    setup_logger(out_base / "logs/pipeline.log")
    start = time.perf_counter()

    logger.info("CSV extraction started")
    csv_raw = extract_csv(base / "data/raw/students.csv")
    logger.info("API extraction started")
    api_raw = extract_api(url=os.getenv("API_URL"),
                          mock_path=base / "data/raw/api_mock.json")
    logger.info("Database extraction started")
    db_raw = extract_database(base / "database/students.db")
    logger.info("MongoDB extraction started")
    mongo_raw = extract_mongo_source(base)
    logger.info("Web scraping started")
    web_raw = extract_web(url=os.getenv("WEB_SOURCE_URL"),
                          html_path=base / "data/raw/students_web.html")
    counts = {"CSV": len(csv_raw), "API": len(api_raw), "Database": len(db_raw),
              "MongoDB": len(mongo_raw), "Web": len(web_raw)}
    for name, n in counts.items():
        logger.info("%s records: %d", name, n)

    logger.info("Source validation started")
    csv_valid, csv_rej = validate_student_source(csv_raw)
    api_valid, api_rej = validate_api_source(api_raw)
    db_valid, db_rej = validate_database_source(db_raw)
    mongo_valid, mongo_rej = validate_mongodb_source(mongo_raw)
    web_valid, web_rej = validate_web_source(web_raw)

    csv_valid = clean_students(csv_valid)
    api_valid = clean_api(api_valid)
    mongo_valid = clean_mongodb(mongo_valid)
    web_valid = clean_web(web_valid)

    rejections = [df.assign(source=name) for name, df in [
        ("csv", csv_rej), ("api", api_rej), ("database", db_rej),
        ("mongodb", mongo_rej), ("web", web_rej)]]
    already_rejected = set(
        pd.concat([csv_rej, api_rej, db_rej], ignore_index=True)["student_id"]
        .dropna().astype(int))
    rejections.append(compatibility_rejections(
        {"csv": csv_valid, "api": api_valid, "database": db_valid},
        already_rejected))

    logger.info("Transformation and integration started")
    integrated = integrate_data(csv_valid, api_valid, db_valid,
                                mongo_valid, web_valid)
    transformed = add_derived_columns(integrated)

    final, final_rej = split_final_data(transformed)
    rejections.append(final_rej.assign(source="final_validation"))
    logger.info("Final validation completed")

    rejected = (pd.concat(rejections, ignore_index=True)
                [["student_id", "source", "error_reason"]]
                .drop_duplicates().reset_index(drop=True))

    save_processed_data(final, out_base / "data/processed/final_dataset.csv")
    save_rejected_data(rejected, out_base / "data/rejected/rejected_records.csv")
    save_ml_dataset(final, out_base / "data/ml")

    elapsed = time.perf_counter() - start
    logger.info("Integrated Records: %d", len(transformed))
    logger.info("Valid Records: %d", len(final))
    logger.info("Rejected Records: %d", len(rejected))
    logger.info("Processing Time: %.2f seconds", elapsed)

    print("\n-----------------------------------")
    print("PIPELINE EXECUTION SUMMARY")
    print("-----------------------------------")
    for name, n in counts.items():
        print(f"{name + ' Records':<18}: {n}")
    print(f"{'Integrated':<18}: {len(transformed)}")
    print(f"{'Valid Records':<18}: {len(final)}")
    print(f"{'Rejected Records':<18}: {len(rejected)}")
    print(f"{'Processing Time':<18}: {elapsed:.2f} seconds")
    print("-----------------------------------")
    return final, rejected


if __name__ == "__main__":
    run_pipeline()
