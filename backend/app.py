from flask import Flask
import os
import psycopg2

app = Flask(__name__)

# Conexión a base de datos
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def home():
    return "ControlDocPro conectado a BD 🚀"

@app.route("/test-db")
def test_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        result = cur.fetchone()
        conn.close()
        return f"Conexión exitosa: {result}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
