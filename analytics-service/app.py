import os
from datetime import datetime, timezone
from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=4000)
collection = client[os.getenv("MONGO_DB", "student_analytics")]["results"]

# Development-only data. Replace with a MySQL query at integration time.
DEMO_GRADES = [
    {"user_id": 1, "course_name": "Mathematics", "grade": 65},
    {"user_id": 1, "course_name": "Mathematics", "grade": 70},
    {"user_id": 1, "course_name": "Mathematics", "grade": 80},
    {"user_id": 1, "course_name": "Mathematics", "grade": 90},
    {"user_id": 1, "course_name": "Mathematics", "grade": 95},
    {"user_id": 1, "course_name": "Science", "grade": 88},
    {"user_id": 1, "course_name": "Science", "grade": 92},
]

def calculate_results(grades):
    grouped = {}
    for row in grades:
        key = (row["user_id"], row["course_name"])
        grouped.setdefault(key, []).append(float(row["grade"]))
    results = []
    for (user_id, course), values in grouped.items():
        results.append({
            "user_id": user_id,
            "course_name": course,
            "count": len(values),
            "minimum": min(values),
            "maximum": max(values),
            "average": round(sum(values) / len(values), 2),
            "updated_at": datetime.now(timezone.utc),
        })
    return results

@app.get("/health")
def health():
    try:
        client.admin.command("ping")
        return jsonify(status="ok"), 200
    except Exception:
        return jsonify(status="unhealthy"), 503

@app.post("/refresh")
def refresh():
    if os.getenv("DEMO_MODE") != "true":
        return jsonify(error="MySQL integration not configured yet"), 503
    results = calculate_results(DEMO_GRADES)
    for result in results:
        collection.update_one(
            {"user_id": result["user_id"], "course_name": result["course_name"]},
            {"$set": result},
            upsert=True,
        )
    return jsonify(message="Demo analytics refreshed", updated=len(results))
