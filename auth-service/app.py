import os
from datetime import timedelta

import click
import pymysql
from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

jwt = JWTManager(app)


def get_connection():
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


@app.errorhandler(pymysql.MySQLError)
def database_error(error):
    # Log the error type without credentials or query contents.
    app.logger.error("Database operation failed: %s", type(error).__name__)
    return jsonify(error="Database temporarily unavailable"), 503


@app.post("/auth/login")
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A JSON object is required"), 400

    username = data.get("username")
    password = data.get("password")

    if (
        not isinstance(username, str)
        or not username.strip()
        or len(username.strip()) > 50
        or not isinstance(password, str)
        or not password
    ):
        return jsonify(error="Valid username and password are required"), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, password_hash FROM users WHERE username = %s",
                (username.strip(),),
            )
            user = cursor.fetchone()
    finally:
        connection.close()

    if user is None or not check_password_hash(
        user["password_hash"], password
    ):
        return jsonify(error="Invalid username or password"), 401

    token = create_access_token(identity=str(user["id"]))

    return jsonify(
        access_token=token,
        token_type="Bearer",
        expires_in=900,
    )


@app.post("/auth/verify")
@jwt_required()
def verify():
    return jsonify(user_id=int(get_jwt_identity()))


@app.get("/health")
def health():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    finally:
        connection.close()

    return jsonify(status="healthy")


@app.cli.command("create-user")
@click.argument("username")
@click.password_option(confirmation_prompt=True)
def create_user(username, password):
    """Create a user with a hashed password."""
    username = username.strip()

    if not username or len(username) > 50:
        raise click.ClickException("Username must contain 1–50 characters.")

    if len(password) < 8:
        raise click.ClickException("Use a password of at least 8 characters.")

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, generate_password_hash(password)),
            )
        connection.commit()
    except pymysql.err.IntegrityError:
        connection.rollback()
        raise click.ClickException("Username already exists.")
    finally:
        connection.close()

    click.echo(f"Created user: {username}")