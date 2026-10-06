import logging

import pandas as pd

logger = logging.getLogger("student_data_pipeline")

OVERLAP_COLUMNS = ["student_name", "major", "city"]


def _academic_summary(db: pd.DataFrame) -> pd.DataFrame:
    join = lambda x: "; ".join(sorted(set(map(str, x))))
    return db.groupby("student_id", as_index=False).agg(
        course=("course", join),
        score=("score", "mean"),
        semester=("semester", join),
    )


def _merge_web(merged: pd.DataFrame, web: pd.DataFrame) -> pd.DataFrame:
    """Left-join web data; overlapping columns are compared, not duplicated."""
    web = web.copy()
    out = merged.merge(web, on="student_id", how="left", suffixes=("", "_web"))
    for col in OVERLAP_COLUMNS:
        dup = f"{col}_web"
        if dup not in out:
            continue
        both = out[col].notna() & out[dup].notna()
        left = out.loc[both, col].astype("string").str.strip().str.casefold()
        right = out.loc[both, dup].astype("string").str.strip().str.casefold()
        conflicts = int((left != right).sum())
        if conflicts:
            logger.warning("Web source disagrees with CSV on %s for %d record(s)",
                           col, conflicts)
        out = out.drop(columns=dup)
    return out


def integrate_data(
    students: pd.DataFrame,
    api: pd.DataFrame,
    db: pd.DataFrame,
    mongodb: pd.DataFrame | None = None,
    web: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Integrate sources using student_id.

    CSV, API and SQLite are required (inner join). MongoDB and web data are
    enrichment sources (left join), so a student missing from them is kept.
    """
    merged = students.merge(api, on="student_id", how="inner")
    merged = merged.merge(_academic_summary(db), on="student_id", how="inner")
    if mongodb is not None:
        merged = merged.merge(mongodb, on="student_id", how="left")
    if web is not None:
        merged = _merge_web(merged, web)
    return merged


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
    if "credit_hours" in work:
        work["academic_load"] = work["credit_hours"].apply(
            lambda x: pd.NA if pd.isna(x) else ("Full" if x >= 12 else "Part-time")
        )
    return work
