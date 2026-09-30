from pathlib import Path
import pandas as pd

def extract_csv(path: str | Path) -> pd.DataFrame:
    """Extract student records from CSV without embedding source logic in main.py."""
    return pd.read_csv(path)
