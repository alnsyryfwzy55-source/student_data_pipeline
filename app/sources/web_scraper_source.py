from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


def extract_web(
    url: str | None = None,
    html_path: str | Path | None = None,
    timeout: int = 10,
) -> pd.DataFrame:
    """Extract student rows from an HTML table.

    Uses the URL when given; if the request fails and a local fixture is
    available, falls back to the fixture.
    """
    if url:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            html = response.text
        except requests.RequestException as exc:
            if html_path is None:
                raise RuntimeError(f"Web scraping failed: {exc}") from exc
            html = Path(html_path).read_text(encoding="utf-8")
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
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)

    if len(rows) < 2:
        raise RuntimeError("Student table contains no data rows")

    headers = [h.strip().lower().replace(" ", "_") for h in rows[0]]
    return pd.DataFrame(rows[1:], columns=headers)
