import os
import pandas as pd
from pathlib import Path
import time

from app.sources.csv_source import extract_csv
from app.sources.api_source import extract_api
from app.sources.database_source import extract_database
from app.validation.quality import (
    validate_student_source, validate_api_source,
    validate_database_source, validate_final_data,
    validate_mongodb_source, validate_web_source
)
from app.transformation.cleaner import clean_students, clean_api, clean_mongodb, clean_web
from app.transformation.integration import integrate_data, add_derived_columns
from app.output.csv_writer import save_processed_data, save_rejected_data
from app.utils.logger import setup_logger

from app.sources.mongodb_source import extract_mongodb
from app.sources.web_scraper_source import extract_web

BASE = Path(__file__).resolve().parent
logger = setup_logger(BASE / "logs/pipeline.log")

def run_pipeline():
    start = time.perf_counter()
    logger.info("CSV extraction started")
    csv_raw = extract_csv(BASE / "data/raw/students.csv")
    logger.info("CSV records: %d", len(csv_raw))

    logger.info("API extraction started")
    api_raw = extract_api(mock_path=BASE / "data/raw/api_mock.json")
    logger.info("API records: %d", len(api_raw))

    logger.info("Database extraction started")
    db_raw = extract_database(BASE / "database/students.db")
    logger.info("Database records: %d", len(db_raw))

    web_raw = extract_web(html_path=BASE / "data/raw/students_web.html")

    mongo_uri = os.getenv("MONGO_URI")

    mongo_raw = pd.DataFrame()

    if mongo_uri:
        mongo_raw = extract_mongodb(
            mongo_uri,
            os.getenv(
                "MONGO_DATABASE",
                "student_pipeline",
            ),
            os.getenv(
                "MONGO_COLLECTION",
                "students",
            ),
        )
    else:
        logger.warning(
            "MONGO_URI is not configured; "
            "MongoDB source is skipped"
        )
    logger.info("Source validation started")
    csv_valid, csv_rej = validate_student_source(csv_raw)
    api_valid, api_rej = validate_api_source(api_raw)
    db_valid, db_rej = validate_database_source(db_raw)
    mongo_valid, mongo_rej = validate_mongodb_source(mongo_raw)
    web_valid, web_rej = validate_web_source(web_raw)

    csv_valid = clean_students(csv_valid)
    api_valid = clean_api(api_valid)
    web_valid = clean_web(web_valid)

    if not mongo_raw.empty:
        mongo_valid = clean_mongodb(
            mongo_valid
        )

    else:
        mongo_valid = None

    logger.info("Transformation and integration started")
    integrated = integrate_data(
    csv_valid,
    api_valid,
    db_valid,
    mongo_valid,
    web_valid,)

    transformed = add_derived_columns(integrated)

    # Add cross-source compatibility validation.
    csv_ids = set(csv_valid["student_id"].astype(int))
    api_ids = set(api_valid["student_id"].astype(int))
    db_ids = set(db_valid["student_id"].astype(int))
    compatible = (
        transformed["student_id"].astype(int).isin(csv_ids)
        & transformed["student_id"].astype(int).isin(api_ids)
        & transformed["student_id"].astype(int).isin(db_ids)
    )
    compatibility_rej = transformed.loc[~compatible, ["student_id"]].copy()
    compatibility_rej["error_reason"] = "Incompatible student_id across sources"

    final = validate_final_data(transformed)
    logger.info("Final validation completed")

    rejected = pd.concat(
    [
        csv_rej,
        api_rej,
        db_rej,
        mongo_rej,
        web_rej,
    ],ignore_index=True,).drop_duplicates()
    
    # rejected = (
    #     __import__("pandas").concat(
    #         [csv_rej, api_rej, db_rej, compatibility_rej],
    #         ignore_index=True,
    #     )
    #     .drop_duplicates()
    # )
    save_processed_data(final, BASE / "data/processed/final_dataset.csv")
    save_rejected_data(rejected, BASE / "data/rejected/rejected_records.csv")

    elapsed = time.perf_counter() - start
    logger.info("Final dataset created")
    logger.info("CSV Records: %d", len(csv_raw))
    logger.info("API Records: %d", len(api_raw))
    logger.info("Database Records: %d", len(db_raw))
    logger.info("Integrated Records: %d", len(transformed))
    logger.info("Valid Records: %d", len(final))
    logger.info("Rejected Records: %d", len(rejected))
    logger.info("Processing Time: %.2f seconds", elapsed)

    print("\n-----------------------------------")
    print("PIPELINE EXECUTION SUMMARY")
    print("-----------------------------------")
    print(f"CSV Records       : {len(csv_raw)}")
    print(f"API Records       : {len(api_raw)}")
    print(f"Database Records  : {len(db_raw)}")
    print(f"Integrated Records: {len(transformed)}")
    print(f"Valid Records     : {len(final)}")
    print(f"Rejected Records  : {len(rejected)}")
    print(f"Processing Time   : {elapsed:.2f} seconds")
    print("-----------------------------------")
    return final, rejected

if __name__ == "__main__":
    run_pipeline()
