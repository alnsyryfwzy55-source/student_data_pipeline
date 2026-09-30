import sqlite3
from pathlib import Path
import pandas as pd

def extract_database(path: str | Path) -> pd.DataFrame:
    """Extract enrollment data joined with course metadata from SQLite."""
    query = """
        SELECT e.student_id,
               c.course_name AS course,
               e.semester,
               e.score
        FROM enrollments e
        JOIN courses c ON c.course_id = e.course_id
    """
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(query, conn)
