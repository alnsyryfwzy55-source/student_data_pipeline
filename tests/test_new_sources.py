from pathlib import Path

from app.sources.web_scraper_source import extract_web


BASE = Path(__file__).resolve().parents[1]


def test_web_scraper_loaded():
    df = extract_web(
        html_path=BASE / "data/raw/students_web.html"
    )

    assert not df.empty
    assert "student_id" in df.columns
    assert "scholarship" in df.columns