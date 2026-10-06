from pathlib import Path

import pandas as pd
import pytest

from app.sources.web_scraper_source import extract_web
from app.sources.mongodb_source import extract_mongodb_json

BASE = Path(__file__).resolve().parents[1]


def test_web_scraper_loaded():
    df = extract_web(html_path=BASE / "data/raw/students_web.html")
    assert not df.empty
    assert "student_id" in df.columns
    assert "scholarship" in df.columns


def test_web_requires_a_source():
    with pytest.raises(ValueError):
        extract_web()


def test_web_url_failure_falls_back_to_fixture(monkeypatch):
    import requests
    def boom(*a, **k):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(requests, "get", boom)
    df = extract_web(url="http://unreachable.invalid",
                     html_path=BASE / "data/raw/students_web.html")
    assert not df.empty


def test_mongodb_json_fixture_loaded():
    df = extract_mongodb_json(BASE / "data/raw/mongodb_students.json")
    assert {"student_id", "credit_hours", "enrollment_status"} <= set(df.columns)


def test_mongo_failure_falls_back(monkeypatch):
    import main
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:1")
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(main, "extract_mongodb", boom)
    assert not main.extract_mongo_source(BASE).empty
