"""Load data/raw/mongodb_students.json into a MongoDB collection.

Usage:
    MONGO_URI=mongodb://localhost:27017 python scripts/seed_mongodb.py
Optional: MONGO_DATABASE (default student_pipeline), MONGO_COLLECTION (default students).
"""
import json
import os
import sys
from pathlib import Path

from pymongo import MongoClient, UpdateOne

BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    uri = os.getenv("MONGO_URI")
    if not uri:
        print("MONGO_URI is not set", file=sys.stderr)
        return 1
    documents = json.loads((BASE / "data/raw/mongodb_students.json").read_text(encoding="utf-8"))
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        collection = client[os.getenv("MONGO_DATABASE", "student_pipeline")][
            os.getenv("MONGO_COLLECTION", "students")]
        collection.bulk_write(
            [UpdateOne({"student_id": d["student_id"]}, {"$set": d}, upsert=True)
             for d in documents])
        print(f"Upserted {len(documents)} documents")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
