import pandas as pd

def integrate_data(students: pd.DataFrame, api: pd.DataFrame, db: pd.DataFrame) -> pd.DataFrame:
    """Integrate all three sources using student_id."""
    academic = (
        db.groupby("student_id", as_index=False)
          .agg(course=("course", lambda x: "; ".join(sorted(set(map(str, x))))),
               score=("score", "mean"),
               semester=("semester", lambda x: "; ".join(sorted(set(map(str, x))))))
    )
    merged = students.merge(api, on="student_id", how="inner")
    return merged.merge(academic, on="student_id", how="inner")

def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["performance_level"] = pd.cut(
        work["gpa"],
        bins=[-float("inf"), 2.0, 2.5, 3.0, 3.5, float("inf")],
        labels=["At Risk", "Acceptable", "Good", "Very Good", "Excellent"],
        right=False,
    )
    work["attendance_status"] = work["attendance"].apply(
        lambda x: "Good" if x >= 75 else "Low"
    )
    return work
