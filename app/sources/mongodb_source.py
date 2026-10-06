import json
from pathlib import Path
from typing import Any

import pandas as pd


def extract_mongodb(
    uri: str,
    database: str,
    collection: str,
    query: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Extract student documents from MongoDB into a DataFrame."""
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise RuntimeError("pymongo is required for MongoDB extraction") from exc

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        documents = list(client[database][collection].find(query or {}, {"_id": 0}))
    finally:
        client.close()

    if not documents:
        raise RuntimeError("MongoDB collection returned no documents")
    return pd.DataFrame(documents)


def extract_mongodb_json(path: str | Path) -> pd.DataFrame:
    """Offline fallback: read the same documents from a local JSON export."""
    try:
        documents = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid MongoDB fixture: {exc}") from exc
    if not documents:
        raise RuntimeError("MongoDB fixture is empty")
    return pd.DataFrame(documents)
