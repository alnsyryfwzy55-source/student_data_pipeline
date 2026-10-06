from pathlib import Path
import json
import logging
import pandas as pd
import requests

def extract_api(url: str | None = None, mock_path: str | Path | None = None,
                timeout: int = 10) -> pd.DataFrame:
    """Extract JSON from REST API; use local mock when no URL is configured."""
    if url:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if not data:
                raise ValueError("API returned an empty response")
            return pd.DataFrame(data)
        except (requests.RequestException, ValueError) as exc:
            if mock_path is None:
                raise RuntimeError(f"API extraction failed: {exc}") from exc
            logging.getLogger("student_data_pipeline").warning(
                "API request failed (%s); using local mock", exc)

    if mock_path is None:
        raise RuntimeError("No API URL or mock source configured")

    path = Path(mock_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid mock API data: {exc}") from exc

    if not data:
        raise RuntimeError("API mock returned an empty response")
    return pd.DataFrame(data)
