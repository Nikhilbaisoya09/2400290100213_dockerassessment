import os
import time
import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

REGNO = os.getenv("REGNO", "not-set")
APP_VERSION = os.getenv("APP_VERSION", "0.1")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME", "festpass"),
        user=os.getenv("DB_USER", "festpass"),
        password=os.getenv("DB_PASSWORD", ""),
        connect_timeout=2
    )


def initialize_database():
    for attempt in range(10):
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
            cursor.close()
            connection.close()
            print("Database initialized successfully")
            return
        except Exception as error:
            print(f"Database attempt {attempt + 1}/10 failed: {error}")
            time.sleep(3)


@app.get("/api/health")
def health():
    database_connected = False

    try:
        connection = get_connection()
        connection.close()
        database_connected = True
    except Exception:
        pass

    return jsonify({
        "status": "healthy" if database_connected else "database_unavailable",
        "database_connected": database_connected,
        "registration_number": REGNO,
        "app_version": APP_VERSION
    }), 200 if database_connected else 503


@app.get("/api/registrations")
def get_registrations():
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id, name, email, created_at FROM registrations ORDER BY id DESC"
        )
        rows = cursor.fetchall()

        registrations = [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "created_at": row[3].isoformat()
            }
            for row in rows
        ]

        cursor.close()
        connection.close()
        return jsonify(registrations)
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.post("/api/registrations")
def create_registration():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO registrations (name, email) VALUES (%s, %s) RETURNING id",
            (name, email)
        )
        registration_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({
            "message": "Registration successful",
            "id": registration_id,
            "name": name,
            "email": email
        }), 201
    except Exception as error:
        return jsonify({"error": str(error)}), 500


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000)
