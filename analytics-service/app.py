import os
from datetime import datetime, timezone

import pymysql
from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

client = MongoClient(
    os.environ["MONGO_URI"],
    serverSelectionTimeoutMS=4000,
    connectTimeoutMS=4000,
    socketTimeoutMS=4000,
)

collection = client[
    os.getenv("MONGO_DB", "student_analytics")
]["dashboards"]

def get_mysql_connection():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
    )


def read_grades(user_id=None):
    """Read grades for every user, or only for one user when user_id is given.

    Reading one user uses the (user_id, course_name) index on grades, so the cost
    no longer grows with the total number of users and grades in the system.
    """
    query = """
        SELECT
            u.id AS user_id,
            u.username,
            g.id AS grade_id,
            g.course_name,
            g.grade
        FROM users AS u
        LEFT JOIN grades AS g ON g.user_id = u.id
    """
    params = ()

    if user_id is not None:
        query += " WHERE u.id = %s"
        params = (user_id,)

    query += " ORDER BY u.id, g.course_name, g.id"

    connection = get_mysql_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        connection.close()


def calculate_results(rows):
    users = {}

    for row in rows:
        user_id = row["user_id"]

        if user_id not in users:
            users[user_id] = {
                "user_id": user_id,
                "username": row["username"],
                "grades": [],
            }

        if row["grade_id"] is not None:
            users[user_id]["grades"].append({
                "grade_id": row["grade_id"],
                "course_name": row["course_name"],
                "grade": float(row["grade"]),
            })

    results = []

    for user in users.values():
        values = [item["grade"] for item in user["grades"]]

        user["summary"] = {
            "count": len(values),
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "average": (
                round(sum(values) / len(values), 2)
                if values else None
            ),
        }

        user["updated_at"] = datetime.now(timezone.utc)
        results.append(user)

    return results


@app.get("/health")
def health():
    try:
        connection = get_mysql_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        finally:
            connection.close()

        client.admin.command("ping")

        return jsonify(status="ok"), 200

    except (pymysql.MySQLError, PyMongoError) as error:
        app.logger.error(
            "Health check failed: %s",
            type(error).__name__,
        )
        return jsonify(status="unhealthy"), 503


@app.post("/refresh")
def refresh():
    # Optional {"user_id": N}: recalculate only that user instead of everyone.
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") if isinstance(data, dict) else None

    if user_id is not None and (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or user_id <= 0
    ):
        return jsonify(error="user_id must be a positive integer"), 400

    try:
        rows = read_grades(user_id)
        results = calculate_results(rows)

        for result in results:
            collection.update_one(
                {"user_id": result["user_id"]},
                {"$set": result},
                upsert=True,
            )

        return jsonify(
            message="Analytics refreshed from MySQL",
            grades_read=sum(len(user["grades"]) for user in results),
            updated=len(results),
        ), 200

    except (pymysql.MySQLError, PyMongoError) as error:
        app.logger.error(
            "Analytics refresh failed: %s",
            type(error).__name__,
        )
        return jsonify(
            error="A required database is temporarily unavailable"
        ), 503