from flask import Flask
import os
import psycopg2

app = Flask(__name__)

# Toma la URL de la base de datos desde las variables de entorno de Render
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        raise Exception("La variable de entorno DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def home():
    return "ControlDocPro conectado 🚀"

@app.route("/test-db")
def test_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return f"Conexión exitosa a PostgreSQL: {result}"
    except Exception as e:
        return f"Error de conexión a la base de datos: {str(e)}"

@app.route("/create-users-table")
def create_users_table():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            rol VARCHAR(50) NOT NULL,
            estado BOOLEAN DEFAULT TRUE,
            ultimo_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        conn.close()

        return "Tabla users creada correctamente 🚀"

    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
