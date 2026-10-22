import os
from decimal import Decimal, InvalidOperation

import pymysql
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

AUTH_URL = os.environ["AUTH_URL"]


def get_connection():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
    )


@app.errorhandler(pymysql.MySQLError)
def database_error(error):
    app.logger.error("Database operation failed: %s", type(error).__name__)
    return jsonify(error="Database temporarily unavailable"), 503


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/login")
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A JSON object is required"), 400

    try:
        response = requests.post(
            f"{AUTH_URL}/auth/login",
            json={
                "username": data.get("username"),
                "password": data.get("password"),
            },
            timeout=5,
        )
        result = response.json()
    except (requests.RequestException, ValueError):
        return jsonify(error="Authentication service unavailable"), 503

    if response.status_code not in (200, 400, 401):
        return jsonify(error="Authentication service unavailable"), 503

    return jsonify(result), response.status_code


@app.post("/api/grades")
def add_grade():
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return jsonify(error="Login required"), 401

    try:
        response = requests.post(
            f"{AUTH_URL}/auth/verify",
            headers={"Authorization": authorization},
            timeout=5,
        )

        if response.status_code in (401, 422):
            return jsonify(error="Invalid or expired token. Log in again."), 401

        if response.status_code != 200:
            return jsonify(error="Authentication service unavailable"), 503

        user_id = int(response.json()["user_id"])

        if user_id <= 0:
            raise ValueError("Invalid user ID")
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return jsonify(error="Authentication service unavailable"), 503

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A JSON object is required"), 400

    course_name = data.get("course_name")
    raw_grade = data.get("grade")

    if (
        not isinstance(course_name, str)
        or not course_name.strip()
        or len(course_name.strip()) > 100
    ):
        return jsonify(error="Course name must contain 1–100 characters"), 400

    if isinstance(raw_grade, bool) or not isinstance(
        raw_grade, (str, int, float)
    ):
        return jsonify(error="Grade must be a number"), 400

    try:
        grade = Decimal(str(raw_grade))
    except InvalidOperation:
        return jsonify(error="Grade must be a number"), 400

    if not grade.is_finite() or not 0 <= grade <= 100:
        return jsonify(error="Grade must be between 0 and 100"), 400

    if grade != grade.quantize(Decimal("0.01")):
        return jsonify(error="Grade can have at most two decimal places"), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO grades (user_id, course_name, grade)
                VALUES (%s, %s, %s)
                """,
                (user_id, course_name.strip(), grade),
            )
            grade_id = cursor.lastrowid

        connection.commit()
    finally:
        connection.close()

    return jsonify(
        message="Grade saved successfully",
        id=grade_id,
    ), 201


@app.get("/health")
def health():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    finally:
        connection.close()

    return jsonify(status="healthy")