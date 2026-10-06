from pathlib import Path
import pandas as pd

from app.sources.csv_source import extract_csv
from app.sources.api_source import extract_api
from app.sources.database_source import extract_database
from app.validation.quality import validate_student_source
from app.transformation.integration import integrate_data
from app.transformation.cleaner import clean_students

BASE = Path(__file__).resolve().parents[1]

def test_csv_loaded():
    df = extract_csv(BASE / "data/raw/students.csv")
    assert not df.empty

def test_api_loaded():
    df = extract_api(mock_path=BASE / "data/raw/api_mock.json")
    assert not df.empty

def test_sqlite_loaded():
    df = extract_database(BASE / "database/students.db")
    assert not df.empty

def test_duplicates_removed():
    raw = extract_csv(BASE / "data/raw/students.csv")
    valid, rejected = validate_student_source(raw)
    assert len(valid) < len(raw)
    assert (rejected["error_reason"] == "Duplicate student_id").any()

def test_missing_values_handled():
    raw = extract_csv(BASE / "data/raw/students.csv")
    valid, _ = validate_student_source(raw)
    assert valid["age"].isna().any()  # kept by validation, imputed by cleaning
    cleaned = clean_students(valid)
    assert cleaned["age"].notna().all()

def test_invalid_records_rejected():
    raw = extract_csv(BASE / "data/raw/students.csv")
    _, rejected = validate_student_source(raw)
    assert (rejected["error_reason"] == "Invalid Age").any()

def test_integration():
    students = pd.DataFrame({
        "student_id":[1], "student_name":["A"], "age":[20],
        "major":["CS"], "city":["Sanaa"]
    })
    api = pd.DataFrame({
        "student_id":[1], "gpa":[3.5], "attendance":[90], "status":["Active"]
    })
    db = pd.DataFrame({
        "student_id":[1], "course":["Python"], "semester":["2026"], "score":[90]
    })
    result = integrate_data(students, api, db)
    assert len(result) == 1
    assert result.iloc[0]["student_id"] == 1

def test_final_dataset_created(tmp_path):
    from main import run_pipeline
    before = (BASE / "data/processed").exists()
    final, rejected = run_pipeline(out_base=tmp_path)
    assert (tmp_path / "data/processed/final_dataset.csv").exists()
    assert (tmp_path / "data/ml/ml_ready_dataset.csv").exists()
    assert (tmp_path / "data/ml/feature_schema.json").exists()
    assert list(rejected.columns) == ["student_id", "source", "error_reason"]
    assert len(final) > 0
    assert before == (BASE / "data/processed").exists()  # repo outputs untouched
