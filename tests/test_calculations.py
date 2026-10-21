import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analytics-service"))
# app.py requires MONGO_URI to be set at import time; use a dummy URI for unit tests.
import os
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
from app import calculate_results

def test_statistics():
    result = calculate_results([
        {"user_id": 1, "course_name": "Math", "grade": 60},
        {"user_id": 1, "course_name": "Math", "grade": 80},
    ])[0]
    assert (result["count"], result["minimum"], result["maximum"], result["average"]) == (2, 60, 80, 70)
