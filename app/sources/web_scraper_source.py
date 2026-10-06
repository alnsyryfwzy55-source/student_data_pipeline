from bs4 import BeautifulSoup
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


def extract_web(
    url: str | None = None,
    html_path: str | Path | None = None,
) -> pd.DataFrame:
    """Extract student rows from an HTML table, from URL or local fixture."""

    if url:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        html = response.text

    elif html_path:
        html = Path(html_path).read_text(encoding="utf-8")

    else:
        raise ValueError("Provide url or html_path")

    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", id="students") or soup.find("table")

    if table is None:
        raise RuntimeError("No student table found in HTML")

    rows = []

    for tr in table.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in tr.find_all(["th", "td"])
        ]

        if cells:
            rows.append(cells)

    if len(rows) < 2:
        raise RuntimeError("Student table contains no data rows")

    headers = [
        header.strip().lower().replace(" ", "_")
        for header in rows[0]
    ]

    return pd.DataFrame(rows[1:], columns=headers)