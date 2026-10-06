import pandas as pd

def validate_student_source(df: pd.DataFrame):
    """Return cleaned valid rows and rejected rows with reasons."""
    work = df.copy()
    rejected = []

    # Normalize column names.
    work.columns = (
        work.columns.str.strip().str.lower()
        .str.replace(" ", "_", regex=False)
    )

    # Required field.
    missing_id = work["student_id"].isna()
    for idx in work.index[missing_id]:
        rejected.append((work.loc[idx].to_dict(), "Missing student_id"))

    # Type conversion before range validation.
    work["student_id"] = pd.to_numeric(work["student_id"], errors = "coerce")
    work["age"] = pd.to_numeric(work["age"], errors="coerce")

    bad_id = work["student_id"].isna() & ~missing_id
    for idx in work.index[bad_id]:
        rejected.append((work.loc[idx].to_dict(), "Invalid student_id"))

    # Duplicates: keep first occurrence.
    duplicate_mask = work["student_id"].duplicated(keep="first") & work["student_id"].notna()
    for idx in work.index[duplicate_mask]:
        rejected.append((work.loc[idx].to_dict(), "Duplicate student_id"))

    # Age rule.
    bad_age = work["age"].notna() & ~work["age"].between(16, 80)
    for idx in work.index[bad_age]:
        rejected.append((work.loc[idx].to_dict(), "Invalid Age"))

    # Missing age is retained for later imputation.
    valid_mask = ~(missing_id | bad_id | duplicate_mask | bad_age)
    valid = work.loc[valid_mask].copy()
    rejected_df = pd.DataFrame(
        [{"student_id": r.get("student_id"), "error_reason": reason}
         for r, reason in rejected]
    )
    return valid, rejected_df

def validate_api_source(df: pd.DataFrame):
    work = df.copy()
    work["student_id"] = pd.to_numeric(work["student_id"], errors="coerce")
    work["gpa"] = pd.to_numeric(work["gpa"], errors="coerce")
    work["attendance"] = pd.to_numeric(work["attendance"], errors="coerce")
    rejected = []

    bad_id = work["student_id"].isna()
    for idx in work.index[bad_id]:
        rejected.append((work.loc[idx, "student_id"], "Missing/Invalid student_id"))

    bad_gpa = work["gpa"].notna() & ~work["gpa"].between(0, 4)
    for idx in work.index[bad_gpa]:
        rejected.append((work.loc[idx, "student_id"], "Invalid GPA"))

    bad_att = work["attendance"].notna() & ~work["attendance"].between(0, 100)
    for idx in work.index[bad_att]:
        rejected.append((work.loc[idx, "student_id"], "Invalid Attendance"))

    dup = _duplicates(work)
    for idx in work.index[dup]:
        rejected.append((work.loc[idx, "student_id"], "Duplicate student_id"))

    invalid = bad_id | bad_gpa | bad_att | dup
    valid = work.loc[~invalid].copy()
    rejected_df = pd.DataFrame(rejected, columns=["student_id", "error_reason"])
    return valid, rejected_df

def validate_database_source(df: pd.DataFrame):
    work = df.copy()
    work["student_id"] = pd.to_numeric(work["student_id"], errors="coerce")
    work["score"] = pd.to_numeric(work["score"], errors="coerce")
    bad_score = work["score"].notna() & ~work["score"].between(0, 100)
    rejected = pd.DataFrame({
        "student_id": work.loc[bad_score, "student_id"],
        "error_reason": "Invalid Score"
    })
    return work.loc[~bad_score].copy(), rejected

FINAL_RULES = [
    ("student_id", lambda d: d["student_id"].notna(), "Missing student_id"),
    ("age", lambda d: d["age"].between(16, 80), "Final check: invalid or missing age"),
    ("gpa", lambda d: d["gpa"].between(0, 4), "Final check: invalid or missing gpa"),
    ("attendance", lambda d: d["attendance"].between(0, 100),
     "Final check: invalid or missing attendance"),
    ("score", lambda d: d["score"].between(0, 100),
     "Final check: invalid or missing score"),
]


def split_final_data(df: pd.DataFrame):
    """Final gate: return (valid rows, rejected rows with reasons)."""
    reasons = pd.Series("", index=df.index)
    for _, rule, message in FINAL_RULES:
        failed = ~rule(df).fillna(False).astype(bool)
        reasons = reasons.where(~failed | (reasons != ""), message)
    bad = reasons != ""
    rejected = pd.DataFrame({
        "student_id": df.loc[bad, "student_id"],
        "error_reason": reasons[bad],
    })
    return df.loc[~bad].copy(), rejected.reset_index(drop=True)


def validate_final_data(df: pd.DataFrame) -> pd.DataFrame:
    return split_final_data(df)[0]


def _duplicates(work: pd.DataFrame):
    """Mask of repeated student_id values (first occurrence is kept)."""
    return work["student_id"].duplicated(keep="first") & work["student_id"].notna()


def validate_mongodb_source(df: pd.DataFrame):
    work = df.copy()

    if work.empty:
        return (
            pd.DataFrame(columns=work.columns),
            pd.DataFrame(columns=["student_id", "error_reason"]),
        )

    if "student_id" not in work.columns:
        rejected = pd.DataFrame(
            {
                "student_id": [None] * len(work),
                "error_reason": ["Missing student_id"] * len(work),
            },
        )
        return pd.DataFrame(columns=work.columns), rejected.reset_index(drop=True)

    work["student_id"] = pd.to_numeric(
        work["student_id"],
        errors="coerce",
    )

    if "credit_hours" in work:
        work["credit_hours"] = pd.to_numeric(
            work["credit_hours"],
            errors="coerce",
        )

    bad_id = work["student_id"].isna()

    if "credit_hours" in work:
        bad_hours = (
            work["credit_hours"].notna()
            & ~work["credit_hours"].between(0, 30)
        )
    else:
        bad_hours = False

    dup = _duplicates(work)

    rejected = pd.DataFrame(
        [
            *[
                (work.loc[i, "student_id"], "Duplicate student_id")
                for i in work.index[dup]
            ],
            *[
                (
                    work.loc[i, "student_id"],
                    "Missing/Invalid student_id",
                )
                for i in work.index[bad_id]
            ],
            *[
                (
                    work.loc[i, "student_id"],
                    "Invalid credit_hours",
                )
                for i in work.index[bad_hours]
            ],
        ],
        columns=[
            "student_id",
            "error_reason",
        ],
    )

    return (
        work.loc[~(bad_id | bad_hours | dup)].copy(),
        rejected,
    )


def validate_web_source(df: pd.DataFrame):
    work = df.copy()
    work["student_id"] = pd.to_numeric(work["student_id"], errors="coerce")

    bad_id = work["student_id"].isna()
    dup = _duplicates(work)

    rejected = pd.concat([
        pd.DataFrame({
            "student_id": work.loc[bad_id, "student_id"],
            "error_reason": "Missing/Invalid student_id",
        }),
        pd.DataFrame({
            "student_id": work.loc[dup, "student_id"],
            "error_reason": "Duplicate student_id",
        }),
    ], ignore_index=True)
    return work.loc[~(bad_id | dup)].copy(), rejected
