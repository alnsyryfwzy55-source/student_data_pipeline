import pandas as pd

def clean_students(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = (
        work.columns.str.strip().str.lower()
        .str.replace(" ", "_", regex=False)
    )
    for col in ["student_name", "major", "city"]:
        if col in work:
            work[col] = work[col].astype("string").str.strip()
    if "city" in work:
        work["city"] = work["city"].str.upper().str.title()
    if "age" in work:
        work["age"] = pd.to_numeric(work["age"], errors="coerce")
        if work["age"].notna().any():
            work["age"] = work["age"].fillna(work["age"].median())
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
