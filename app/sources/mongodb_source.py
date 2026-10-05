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
        raise RuntimeError(
            "pymongo is required for MongoDB extraction"
        ) from exc

    client = MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
    )

    try:
        client.admin.command("ping")

        documents = list(
            client[database][collection].find(
                query or {},
                {"_id": 0},
            )
        )

    finally:
        client.close()

    if not documents:
        raise RuntimeError(
            "MongoDB collection returned no documents"
        )

    return pd.DataFrame(documents)