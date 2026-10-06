"""Turn the final dataset into a model-ready feature table.

Steps: drop identifiers, expand multi-valued `course`, one-hot encode
categoricals, cast booleans, standardise numeric features (z-score) and keep
`performance_level` as the target. `gpa` is excluded from the features
because the target is derived from it (target leakage).
"""
import json
from pathlib import Path

import pandas as pd

TARGET = "performance_level"
LEAKAGE = ["gpa"]
IDENTIFIERS = ["student_id", "student_name"]
NUMERIC = ["age", "attendance", "score", "credit_hours"]
CATEGORICAL = ["major", "city", "status", "enrollment_status",
               "attendance_status", "academic_load"]


def prepare_ml_dataset(df: pd.DataFrame):
    """Return (ml_ready DataFrame, schema dict describing the transformation)."""
    work = df.copy()
    target = work[TARGET].astype("string")

    features = pd.DataFrame(index=work.index)

    numeric = [c for c in NUMERIC if c in work]
    scaling = {}
    for col in numeric:
        values = pd.to_numeric(work[col], errors="coerce").astype("float64")
        mean = float(values.mean())
        std = float(values.std(ddof=0))
        values = values.fillna(mean)
        features[col] = (values - mean) / std if std else 0.0
        scaling[col] = {"mean": mean, "std": std}

    if "scholarship" in work:
        features["scholarship"] = work["scholarship"].fillna(False).astype(int)

    if "course" in work:
        courses = work["course"].astype("string").str.get_dummies(sep="; ")
        courses.columns = [
            "course_" + c.strip().lower().replace(" ", "_") for c in courses.columns
        ]
        features = features.join(courses.astype(int))

    categorical = [c for c in CATEGORICAL if c in work]
    if categorical:
        dummies = pd.get_dummies(
            work[categorical].astype("string").fillna("unknown"),
            prefix=categorical, dtype=int,
        )
        dummies.columns = [c.lower().replace(" ", "_") for c in dummies.columns]
        features = features.join(dummies)

    features[TARGET] = target
    schema = {
        "target": TARGET,
        "dropped_identifiers": [c for c in IDENTIFIERS if c in work],
        "dropped_for_leakage": [c for c in LEAKAGE if c in work],
        "scaled_numeric": scaling,
        "feature_columns": [c for c in features.columns if c != TARGET],
    }
    return features, schema


def save_ml_dataset(df: pd.DataFrame, out_dir: str | Path) -> pd.DataFrame:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    features, schema = prepare_ml_dataset(df)
    features.to_csv(out_dir / "ml_ready_dataset.csv", index=False)
    (out_dir / "feature_schema.json").write_text(
        json.dumps(schema, indent=2), encoding="utf-8")
    return features
