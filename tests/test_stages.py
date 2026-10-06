import pandas as pd

from app.transformation.cleaner import clean_students, clean_web, clean_mongodb
from app.transformation.integration import integrate_data, add_derived_columns
from app.validation.quality import (
    validate_mongodb_source, validate_web_source, validate_api_source,
    split_final_data,
)
from app.ml.prepare import prepare_ml_dataset
from main import compatibility_rejections


def test_clean_students_normalises_and_imputes_age():
    df = pd.DataFrame({"student_id": [1, 2, 3], "student_name": [" A ", "B", "C"],
                       "age": [20, None, 22], "major": ["AI", "CS", "CS"],
                       "city": [" SANAA", "aden", "Taiz"]})
    out = clean_students(df)
    assert out["age"].tolist() == [20, 21, 22]
    assert out["city"].tolist() == ["Sanaa", "Aden", "Taiz"]
    assert out["major"].iloc[0] == "Artificial Intelligence"


def test_clean_web_maps_scholarship():
    df = pd.DataFrame({"student_id": ["1", "2"], "scholarship": ["Yes", "no"]})
    assert clean_web(df)["scholarship"].tolist() == [True, False]


def test_duplicates_rejected_in_mongo_web_and_api():
    ids = pd.DataFrame({"student_id": [1, 1, 2]})
    assert (validate_web_source(ids)[1]["error_reason"] == "Duplicate student_id").sum() == 1
    mongo = ids.assign(credit_hours=[10, 10, 99])
    valid, rej = validate_mongodb_source(mongo)
    assert set(rej["error_reason"]) == {"Duplicate student_id", "Invalid credit_hours"}
    api = ids.assign(gpa=[3, 3, 3], attendance=[90, 90, 90])
    assert len(validate_api_source(api)[0]) == 2


def _base_frames():
    students = pd.DataFrame({"student_id": [1, 2], "student_name": ["A", "B"],
                             "age": [20, 21], "major": ["CS", "CS"], "city": ["Sanaa", "Aden"]})
    api = pd.DataFrame({"student_id": [1, 2], "gpa": [3.5, 2.2],
                        "attendance": [90, 70], "status": ["Active", "Active"]})
    db = pd.DataFrame({"student_id": [1, 2], "course": ["Python", "SQL"],
                       "semester": ["S1", "S1"], "score": [90, 70]})
    return students, api, db


def test_enrichment_sources_do_not_drop_students():
    students, api, db = _base_frames()
    mongo = pd.DataFrame({"student_id": [1], "credit_hours": [15], "enrollment_status": ["Active"]})
    web = pd.DataFrame({"student_id": [1], "student_name": ["A"], "major": ["CS"],
                        "city": ["Sanaa"], "scholarship": [True]})
    out = add_derived_columns(integrate_data(students, api, db, mongo, web))
    assert len(out) == 2
    assert not any(c.endswith("_web") for c in out.columns)
    assert out.loc[out.student_id == 1, "academic_load"].iloc[0] == "Full"
    assert pd.isna(out.loc[out.student_id == 2, "academic_load"].iloc[0])


def test_derived_columns():
    students, api, db = _base_frames()
    out = add_derived_columns(integrate_data(students, api, db))
    assert out["performance_level"].astype(str).tolist() == ["Excellent", "Acceptable"]
    assert out["attendance_status"].tolist() == ["Good", "Low"]


def test_final_validation_reports_rejected_rows():
    students, api, db = _base_frames()
    df = add_derived_columns(integrate_data(students, api, db))
    df.loc[1, "attendance"] = None
    valid, rejected = split_final_data(df)
    assert valid["student_id"].tolist() == [1]
    assert rejected["student_id"].tolist() == [2]
    assert "attendance" in rejected["error_reason"].iloc[0]


def test_compatibility_check_finds_missing_ids():
    a = pd.DataFrame({"student_id": [1, 2]})
    b = pd.DataFrame({"student_id": [1]})
    out = compatibility_rejections({"csv": a, "api": b}, already_rejected=set())
    assert out["student_id"].tolist() == [2]
    assert "api" in out["error_reason"].iloc[0]
    assert compatibility_rejections({"csv": a, "api": b}, {2}).empty


def test_ml_dataset_is_numeric_without_leakage():
    students, api, db = _base_frames()
    mongo = pd.DataFrame({"student_id": [1, 2], "credit_hours": [15, 9],
                          "enrollment_status": ["Active", "Probation"]})
    web = pd.DataFrame({"student_id": [1, 2], "scholarship": [True, False]})
    df = add_derived_columns(integrate_data(students, api, db, mongo, web))
    features, schema = prepare_ml_dataset(df)
    x = features.drop(columns="performance_level")
    assert all(pd.api.types.is_numeric_dtype(t) for t in x.dtypes)
    assert not x.isna().any().any()
    assert "gpa" not in features and "student_id" not in features
    assert schema["dropped_for_leakage"] == ["gpa"]
    assert abs(x["age"].mean()) < 1e-9
