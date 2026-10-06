import pandas as pd


MAJOR_ALIASES = {"ai": "Artificial Intelligence"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = (
        work.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    )
    return work


def _normalize_text(work: pd.DataFrame) -> pd.DataFrame:
    for col in ["student_name", "major", "city"]:
        if col in work:
            work[col] = work[col].astype("string").str.strip()
    if "city" in work:
        work["city"] = work["city"].str.upper().str.title()
    if "major" in work:
        work["major"] = work["major"].str.casefold().map(MAJOR_ALIASES).fillna(work["major"])
    return work


def clean_students(df: pd.DataFrame) -> pd.DataFrame:
    work = _normalize_text(_normalize_columns(df))
    if "age" in work:
        work["age"] = pd.to_numeric(work["age"], errors="coerce")
        # Documented strategy: median for missing age.
        if work["age"].notna().any():
            work["age"] = work["age"].fillna(work["age"].median())
        work["age"] = work["age"].round().astype("Int64")
    return work


def clean_api(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    for col in ["gpa", "attendance"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    # Documented strategy: median for missing GPA.
    if work["gpa"].notna().any():
        work["gpa"] = work["gpa"].fillna(work["gpa"].median())
    work["status"] = work["status"].astype("string").str.strip().str.title()
    return work


def clean_mongodb(df: pd.DataFrame) -> pd.DataFrame:
    work = _normalize_columns(df)
    for col in ["student_id", "credit_hours"]:
        if col in work:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    if "enrollment_status" in work:
        work["enrollment_status"] = (
            work["enrollment_status"].astype("string").str.strip().str.title()
        )
    return work


def clean_web(df: pd.DataFrame) -> pd.DataFrame:
    work = _normalize_text(_normalize_columns(df))
    work["student_id"] = pd.to_numeric(work["student_id"], errors="coerce")
    if "scholarship" in work:
        work["scholarship"] = (
            work["scholarship"].astype("string").str.strip().str.lower()
            .map({"yes": True, "no": False, "true": True, "false": False})
            .astype("boolean")
        )
    return work
