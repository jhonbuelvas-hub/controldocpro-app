from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import uuid
from werkzeug.utils import secure_filename


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "contract_documents")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "controldocpro-dev-key")

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_connection():
    if not DATABASE_URL:
        raise Exception("La variable de entorno DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Debe iniciar sesión para continuar.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def create_contract_documents_table_if_needed():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contract_documents (
            id SERIAL PRIMARY KEY,
            contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            tipo_documento VARCHAR(100) NOT NULL,
            titulo VARCHAR(200) NOT NULL,
            descripcion TEXT,
            nombre_archivo_original VARCHAR(255) NOT NULL,
            nombre_archivo_guardado VARCHAR(255) NOT NULL,
            ruta_archivo VARCHAR(500) NOT NULL,
            extension_archivo VARCHAR(20),
            tamano_archivo INTEGER,
            version VARCHAR(20) DEFAULT '1.0',
            estado VARCHAR(30) DEFAULT 'ACTIVO',
            usuario_cargue_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def create_users_table_if_needed():
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
    cur.close()
    conn.close()


def create_third_parties_table_if_needed():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS third_parties (
            id SERIAL PRIMARY KEY,
            tipo_tercero VARCHAR(50) NOT NULL,
            nombre VARCHAR(150) NOT NULL,
            identificacion VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(150),
            telefono VARCHAR(30),
            direccion VARCHAR(200),
            ciudad VARCHAR(100),
            representante_legal VARCHAR(150),
            cargo_contacto VARCHAR(100),
            estado BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def create_contracts_table_if_needed():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id SERIAL PRIMARY KEY,
            numero_contrato VARCHAR(100) UNIQUE NOT NULL,
            objeto TEXT NOT NULL,
            tipo_contrato VARCHAR(100) NOT NULL,
            estado_contrato VARCHAR(50) NOT NULL,
            valor_inicial NUMERIC(14,2) NOT NULL DEFAULT 0,
            valor_total NUMERIC(14,2) NOT NULL DEFAULT 0,
            fecha_suscripcion DATE,
            fecha_inicio DATE,
            fecha_fin DATE,
            contratista_id INTEGER NOT NULL REFERENCES third_parties(id),
            supervisor_id INTEGER REFERENCES third_parties(id),
            usuario_creador_id INTEGER REFERENCES users(id),
            observaciones TEXT,
            activo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/health")
def health():
    return "OK"


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
        create_users_table_if_needed()
        return "Tabla users creada correctamente 🚀"
    except Exception as e:
        return f"Error al crear la tabla users: {str(e)}"


@app.route("/create-third-parties-table")
@login_required
def create_third_parties_table():
    try:
        create_third_parties_table_if_needed()
        return "Tabla third_parties creada correctamente 🚀"
    except Exception as e:
        return f"Error al crear la tabla third_parties: {str(e)}"


@app.route("/migrate-passwords")
def migrate_passwords():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, password FROM users")
        users = cur.fetchall()

        updated = 0
        for user in users:
            current_password = user["password"]
            if not current_password.startswith("scrypt:") and not current_password.startswith("pbkdf2:"):
                hashed_password = generate_password_hash(current_password)
                cur.execute(
                    "UPDATE users SET password = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (hashed_password, user["id"])
                )
                updated += 1

        conn.commit()
        cur.close()
        conn.close()

        return f"Migración completada. Contraseñas actualizadas: {updated}"
    except Exception as e:
        return f"Error en migración de contraseñas: {str(e)}"


@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        create_users_table_if_needed()

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "").strip()

            if not email or not password:
                flash("Debe ingresar correo y contraseña.", "error")
                return render_template("login.html")

            conn = get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, nombre, email, password, rol, estado
                FROM users
                WHERE email = %s
            """, (email,))
            user = cur.fetchone()

            if not user:
                cur.close()
                conn.close()
                flash("Usuario o contraseña inválidos.", "error")
                return render_template("login.html")

            if not user["estado"]:
                cur.close()
                conn.close()
                flash("El usuario está inactivo. Contacte al administrador.", "error")
                return render_template("login.html")

            if not check_password_hash(user["password"], password):
                cur.close()
                conn.close()
                flash("Usuario o contraseña inválidos.", "error")
                return render_template("login.html")

            cur.execute("""
                UPDATE users
                SET ultimo_login = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (user["id"],))
            conn.commit()

            session["user_id"] = user["id"]
            session["user_nombre"] = user["nombre"]
            session["user_email"] = user["email"]
            session["user_rol"] = user["rol"]

            cur.close()
            conn.close()

            flash(f"Bienvenido, {user['nombre']}.", "success")
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    except Exception as e:
        return f"Error en login: {str(e)}"


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    try:
        
        create_users_table_if_needed()
        create_third_parties_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT COUNT(*) AS total FROM users")
        total_users = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM users WHERE estado = TRUE")
        active_users = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM third_parties")
        total_third_parties = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM third_parties WHERE estado = TRUE")
        active_third_parties = cur.fetchone()["total"]

        cur.execute("""
            SELECT id, nombre, email, rol, created_at
            FROM users
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_users = cur.fetchall()

        cur.execute("""
            SELECT id, tipo_tercero, nombre, identificacion, ciudad, created_at
            FROM third_parties
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_third_parties = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            "dashboard.html",
            total_users=total_users,
            active_users=active_users,
            total_third_parties=total_third_parties,
            active_third_parties=active_third_parties,
            recent_users=recent_users,
            recent_third_parties=recent_third_parties
            
        )
    
    
    except Exception as e:
        return f"Error en dashboard: {str(e)}"

    


@app.route("/users")
@login_required
def list_users():
    try:
        create_users_table_if_needed()

        search = request.args.get("search", "").strip()
        rol = request.args.get("rol", "").strip()
        estado = request.args.get("estado", "").strip()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, nombre, email, rol, estado, created_at, updated_at, ultimo_login
            FROM users
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (LOWER(nombre) LIKE %s OR LOWER(email) LIKE %s)"
            like_value = f"%{search.lower()}%"
            params.extend([like_value, like_value])

        if rol:
            query += " AND rol = %s"
            params.append(rol)

        if estado == "activo":
            query += " AND estado = TRUE"
        elif estado == "inactivo":
            query += " AND estado = FALSE"

        query += " ORDER BY id DESC"

        cur.execute(query, params)
        users = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            "users.html",
            users=users,
            search=search,
            rol=rol,
            estado=estado
        )
    except Exception as e:
        return f"Error al listar usuarios: {str(e)}"


def validate_user_form(nombre, email, password, rol, is_edit=False):
    errors = []
    roles_validos = ["ADMIN", "JURIDICO", "SUPERVISOR", "FINANCIERO", "CONSULTA"]

    if not nombre or len(nombre.strip()) < 3:
        errors.append("El nombre es obligatorio y debe tener al menos 3 caracteres.")

    if not email or "@" not in email or "." not in email:
        errors.append("Debe ingresar un correo electrónico válido.")

    if not is_edit and (not password or len(password) < 6):
        errors.append("La contraseña es obligatoria y debe tener al menos 6 caracteres.")

    if password and len(password) < 6:
        errors.append("La contraseña debe tener al menos 6 caracteres.")

    if rol not in roles_validos:
        errors.append("Debe seleccionar un rol válido.")

    return errors


@app.route("/users/new", methods=["GET", "POST"])
@login_required
def new_user():
    try:
        create_users_table_if_needed()

        if request.method == "POST":
            nombre = request.form.get("nombre", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "").strip()
            rol = request.form.get("rol", "").strip()

            errors = validate_user_form(nombre, email, password, rol, is_edit=False)

            if errors:
                for error in errors:
                    flash(error, "error")
                user = {
                    "nombre": nombre,
                    "email": email,
                    "rol": rol,
                    "estado": True
                }
                return render_template("user_form.html", title="Nuevo Usuario", user=user, is_edit=False)

            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_user = cur.fetchone()

            if existing_user:
                cur.close()
                conn.close()
                flash("Ya existe un usuario con ese correo electrónico.", "error")
                user = {
                    "nombre": nombre,
                    "email": email,
                    "rol": rol,
                    "estado": True
                }
                return render_template("user_form.html", title="Nuevo Usuario", user=user, is_edit=False)

            hashed_password = generate_password_hash(password)

            cur.execute("""
                INSERT INTO users (nombre, email, password, rol, estado)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (nombre, email, hashed_password, rol))

            conn.commit()
            cur.close()
            conn.close()

            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("list_users"))

        return render_template("user_form.html", title="Nuevo Usuario", user=None, is_edit=False)

    except Exception as e:
        return f"Error al crear usuario: {str(e)}"


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    try:
        create_users_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, nombre, email, rol, estado
            FROM users
            WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return "Usuario no encontrado."

        if request.method == "POST":
            nombre = request.form.get("nombre", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "").strip()
            rol = request.form.get("rol", "").strip()
            estado_form = request.form.get("estado", "activo")
            estado_bool = True if estado_form == "activo" else False

            errors = validate_user_form(nombre, email, password, rol, is_edit=True)

            if errors:
                for error in errors:
                    flash(error, "error")
                user["nombre"] = nombre
                user["email"] = email
                user["rol"] = rol
                user["estado"] = estado_bool
                cur.close()
                conn.close()
                return render_template("user_form.html", title="Editar Usuario", user=user, is_edit=True)

            cur.execute("SELECT id FROM users WHERE email = %s AND id <> %s", (email, user_id))
            existing_user = cur.fetchone()

            if existing_user:
                flash("Ya existe otro usuario con ese correo electrónico.", "error")
                user["nombre"] = nombre
                user["email"] = email
                user["rol"] = rol
                user["estado"] = estado_bool
                cur.close()
                conn.close()
                return render_template("user_form.html", title="Editar Usuario", user=user, is_edit=True)

            if password:
                hashed_password = generate_password_hash(password)
                cur.execute("""
                    UPDATE users
                    SET nombre = %s,
                        email = %s,
                        password = %s,
                        rol = %s,
                        estado = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (nombre, email, hashed_password, rol, estado_bool, user_id))
            else:
                cur.execute("""
                    UPDATE users
                    SET nombre = %s,
                        email = %s,
                        rol = %s,
                        estado = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (nombre, email, rol, estado_bool, user_id))

            conn.commit()
            cur.close()
            conn.close()

            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("list_users"))

        cur.close()
        conn.close()
        return render_template("user_form.html", title="Editar Usuario", user=user, is_edit=True)

    except Exception as e:
        return f"Error al editar usuario: {str(e)}"


@app.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
def toggle_user_status(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, estado FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            flash("Usuario no encontrado.", "error")
            return redirect(url_for("list_users"))

        new_status = not user["estado"]

        cur.execute("""
            UPDATE users
            SET estado = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_status, user_id))

        conn.commit()
        cur.close()
        conn.close()

        if new_status:
            flash("Usuario activado correctamente.", "success")
        else:
            flash("Usuario desactivado correctamente.", "success")

        return redirect(url_for("list_users"))

    except Exception as e:
        return f"Error al cambiar estado del usuario: {str(e)}"


def validate_third_party_form(tipo_tercero, nombre, identificacion, email):
    errors = []
    tipos_validos = [
        "CONTRATISTA",
        "CONTRATANTE",
        "SUPERVISOR",
        "INTERVENTOR",
        "PROVEEDOR",
        "ASEGURADORA",
        "OTRO"
    ]

    if tipo_tercero not in tipos_validos:
        errors.append("Debe seleccionar un tipo de tercero válido.")

    if not nombre or len(nombre.strip()) < 3:
        errors.append("El nombre es obligatorio y debe tener al menos 3 caracteres.")

    if not identificacion or len(identificacion.strip()) < 5:
        errors.append("La identificación es obligatoria y debe tener al menos 5 caracteres.")

    if email and ("@" not in email or "." not in email):
        errors.append("El correo electrónico no es válido.")

    return errors


@app.route("/third-parties")
@login_required
def list_third_parties():
    try:
        create_third_parties_table_if_needed()

        search = request.args.get("search", "").strip()
        tipo = request.args.get("tipo", "").strip()
        estado = request.args.get("estado", "").strip()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, tipo_tercero, nombre, identificacion, email, telefono, ciudad, estado, created_at
            FROM third_parties
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (LOWER(nombre) LIKE %s OR LOWER(identificacion) LIKE %s)"
            like_value = f"%{search.lower()}%"
            params.extend([like_value, like_value])

        if tipo:
            query += " AND tipo_tercero = %s"
            params.append(tipo)

        if estado == "activo":
            query += " AND estado = TRUE"
        elif estado == "inactivo":
            query += " AND estado = FALSE"

        query += " ORDER BY id DESC"

        cur.execute(query, params)
        third_parties = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            "third_parties.html",
            third_parties=third_parties,
            search=search,
            tipo=tipo,
            estado=estado
        )
    except Exception as e:
        return f"Error al listar terceros: {str(e)}"


@app.route("/third-parties/new", methods=["GET", "POST"])
@login_required
def new_third_party():
    try:
        create_third_parties_table_if_needed()

        if request.method == "POST":
            tipo_tercero = request.form.get("tipo_tercero", "").strip()
            nombre = request.form.get("nombre", "").strip()
            identificacion = request.form.get("identificacion", "").strip()
            email = request.form.get("email", "").strip().lower()
            telefono = request.form.get("telefono", "").strip()
            direccion = request.form.get("direccion", "").strip()
            ciudad = request.form.get("ciudad", "").strip()
            representante_legal = request.form.get("representante_legal", "").strip()
            cargo_contacto = request.form.get("cargo_contacto", "").strip()

            errors = validate_third_party_form(tipo_tercero, nombre, identificacion, email)

            if errors:
                for error in errors:
                    flash(error, "error")
                third_party = {
                    "tipo_tercero": tipo_tercero,
                    "nombre": nombre,
                    "identificacion": identificacion,
                    "email": email,
                    "telefono": telefono,
                    "direccion": direccion,
                    "ciudad": ciudad,
                    "representante_legal": representante_legal,
                    "cargo_contacto": cargo_contacto,
                    "estado": True
                }
                return render_template("third_party_form.html", title="Nuevo Tercero", third_party=third_party, is_edit=False)

            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT id FROM third_parties WHERE identificacion = %s", (identificacion,))
            existing = cur.fetchone()

            if existing:
                cur.close()
                conn.close()
                flash("Ya existe un tercero con esa identificación.", "error")
                third_party = {
                    "tipo_tercero": tipo_tercero,
                    "nombre": nombre,
                    "identificacion": identificacion,
                    "email": email,
                    "telefono": telefono,
                    "direccion": direccion,
                    "ciudad": ciudad,
                    "representante_legal": representante_legal,
                    "cargo_contacto": cargo_contacto,
                    "estado": True
                }
                return render_template("third_party_form.html", title="Nuevo Tercero", third_party=third_party, is_edit=False)

            cur.execute("""
                INSERT INTO third_parties (
                    tipo_tercero, nombre, identificacion, email, telefono,
                    direccion, ciudad, representante_legal, cargo_contacto, estado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """, (
                tipo_tercero, nombre, identificacion, email, telefono,
                direccion, ciudad, representante_legal, cargo_contacto
            ))

            conn.commit()
            cur.close()
            conn.close()

            flash("Tercero creado correctamente.", "success")
            return redirect(url_for("list_third_parties"))

        return render_template("third_party_form.html", title="Nuevo Tercero", third_party=None, is_edit=False)

    except Exception as e:
        return f"Error al crear tercero: {str(e)}"


@app.route("/third-parties/<int:third_party_id>/edit", methods=["GET", "POST"])
@login_required
def edit_third_party(third_party_id):
    try:
        create_third_parties_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM third_parties
            WHERE id = %s
        """, (third_party_id,))
        third_party = cur.fetchone()

        if not third_party:
            cur.close()
            conn.close()
            return "Tercero no encontrado."

        if request.method == "POST":
            tipo_tercero = request.form.get("tipo_tercero", "").strip()
            nombre = request.form.get("nombre", "").strip()
            identificacion = request.form.get("identificacion", "").strip()
            email = request.form.get("email", "").strip().lower()
            telefono = request.form.get("telefono", "").strip()
            direccion = request.form.get("direccion", "").strip()
            ciudad = request.form.get("ciudad", "").strip()
            representante_legal = request.form.get("representante_legal", "").strip()
            cargo_contacto = request.form.get("cargo_contacto", "").strip()
            estado_form = request.form.get("estado", "activo")
            estado_bool = True if estado_form == "activo" else False

            errors = validate_third_party_form(tipo_tercero, nombre, identificacion, email)

            if errors:
                for error in errors:
                    flash(error, "error")
                third_party["tipo_tercero"] = tipo_tercero
                third_party["nombre"] = nombre
                third_party["identificacion"] = identificacion
                third_party["email"] = email
                third_party["telefono"] = telefono
                third_party["direccion"] = direccion
                third_party["ciudad"] = ciudad
                third_party["representante_legal"] = representante_legal
                third_party["cargo_contacto"] = cargo_contacto
                third_party["estado"] = estado_bool
                cur.close()
                conn.close()
                return render_template("third_party_form.html", title="Editar Tercero", third_party=third_party, is_edit=True)

            cur.execute("""
                SELECT id FROM third_parties
                WHERE identificacion = %s AND id <> %s
            """, (identificacion, third_party_id))
            existing = cur.fetchone()

            if existing:
                flash("Ya existe otro tercero con esa identificación.", "error")
                third_party["tipo_tercero"] = tipo_tercero
                third_party["nombre"] = nombre
                third_party["identificacion"] = identificacion
                third_party["email"] = email
                third_party["telefono"] = telefono
                third_party["direccion"] = direccion
                third_party["ciudad"] = ciudad
                third_party["representante_legal"] = representante_legal
                third_party["cargo_contacto"] = cargo_contacto
                third_party["estado"] = estado_bool
                cur.close()
                conn.close()
                return render_template("third_party_form.html", title="Editar Tercero", third_party=third_party, is_edit=True)

            cur.execute("""
                UPDATE third_parties
                SET tipo_tercero = %s,
                    nombre = %s,
                    identificacion = %s,
                    email = %s,
                    telefono = %s,
                    direccion = %s,
                    ciudad = %s,
                    representante_legal = %s,
                    cargo_contacto = %s,
                    estado = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                tipo_tercero, nombre, identificacion, email, telefono,
                direccion, ciudad, representante_legal, cargo_contacto,
                estado_bool, third_party_id
            ))

            conn.commit()
            cur.close()
            conn.close()

            flash("Tercero actualizado correctamente.", "success")
            return redirect(url_for("list_third_parties"))

        cur.close()
        conn.close()
        return render_template("third_party_form.html", title="Editar Tercero", third_party=third_party, is_edit=True)

    except Exception as e:
        return f"Error al editar tercero: {str(e)}"


@app.route("/third-parties/<int:third_party_id>/toggle-status", methods=["POST"])
@login_required
def toggle_third_party_status(third_party_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, estado FROM third_parties WHERE id = %s", (third_party_id,))
        third_party = cur.fetchone()

        if not third_party:
            cur.close()
            conn.close()
            flash("Tercero no encontrado.", "error")
            return redirect(url_for("list_third_parties"))

        new_status = not third_party["estado"]

        cur.execute("""
            UPDATE third_parties
            SET estado = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_status, third_party_id))

        conn.commit()
        cur.close()
        conn.close()

        if new_status:
            flash("Tercero activado correctamente.", "success")
        else:
            flash("Tercero desactivado correctamente.", "success")

        return redirect(url_for("list_third_parties"))

    except Exception as e:
        return f"Error al cambiar estado del tercero: {str(e)}"

def validate_contract_form(numero_contrato, objeto, tipo_contrato, estado_contrato, valor_inicial, valor_total, contratista_id):
    errors = []

    tipos_validos = [
        "PRESTACION_SERVICIOS",
        "SUMINISTRO",
        "CONSULTORIA",
        "OBRA",
        "INTERADMINISTRATIVO",
        "COMPRAVENTA",
        "OTRO"
    ]

    estados_validos = [
        "BORRADOR",
        "EN_REVISION",
        "APROBADO",
        "FIRMADO",
        "EN_EJECUCION",
        "SUSPENDIDO",
        "LIQUIDADO",
        "CERRADO"
    ]

    if not numero_contrato or len(numero_contrato.strip()) < 3:
        errors.append("El número de contrato es obligatorio.")

    if not objeto or len(objeto.strip()) < 10:
        errors.append("El objeto contractual es obligatorio y debe ser más descriptivo.")

    if tipo_contrato not in tipos_validos:
        errors.append("Debe seleccionar un tipo de contrato válido.")

    if estado_contrato not in estados_validos:
        errors.append("Debe seleccionar un estado contractual válido.")

    try:
        vi = float(valor_inicial)
        vt = float(valor_total)
        if vi < 0 or vt < 0:
            errors.append("Los valores del contrato no pueden ser negativos.")
    except:
        errors.append("Los valores del contrato deben ser numéricos.")

    if not contratista_id:
        errors.append("Debe seleccionar un contratista.")

    return errors

def validate_contract_document_form(contract_id, tipo_documento, titulo, filename=None, is_edit=False):
    errors = []

    tipos_validos = [
        "CONTRATO",
        "ACTA_INICIO",
        "ACTA_SUSPENSION",
        "ACTA_REINICIO",
        "ACTA_TERMINACION",
        "ACTA_LIQUIDACION",
        "OTROSI",
        "POLIZA",
        "INFORME",
        "OTRO"
    ]

    if not contract_id:
        errors.append("Debe seleccionar un contrato.")

    if tipo_documento not in tipos_validos:
        errors.append("Debe seleccionar un tipo de documento válido.")

    if not titulo or len(titulo.strip()) < 3:
        errors.append("El título es obligatorio y debe tener al menos 3 caracteres.")

    if not is_edit and not filename:
        errors.append("Debe seleccionar un archivo.")

    if filename and not allowed_file(filename):
        errors.append("El tipo de archivo no es permitido.")

    return errors

@app.route("/create-contract-documents-table")
@login_required
def create_contract_documents_table():
    try:
        create_contract_documents_table_if_needed()
        return "Tabla contract_documents creada correctamente 🚀"
    except Exception as e:
        return f"Error al crear la tabla contract_documents: {str(e)}"

@app.route("/create-contracts-table")
@login_required
def create_contracts_table():
    try:
        create_contracts_table_if_needed()
        return "Tabla contracts creada correctamente 🚀"
    except Exception as e:
        return f"Error al crear la tabla contracts: {str(e)}"


@app.route("/contracts")
@login_required
def list_contracts():
    try:
        create_contracts_table_if_needed()
        create_third_parties_table_if_needed()

        search = request.args.get("search", "").strip()
        tipo = request.args.get("tipo", "").strip()
        estado = request.args.get("estado", "").strip()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                c.id,
                c.numero_contrato,
                c.objeto,
                c.tipo_contrato,
                c.estado_contrato,
                c.valor_inicial,
                c.valor_total,
                c.fecha_inicio,
                c.fecha_fin,
                c.activo,
                contratista.nombre AS contratista_nombre,
                supervisor.nombre AS supervisor_nombre
            FROM contracts c
            INNER JOIN third_parties contratista ON c.contratista_id = contratista.id
            LEFT JOIN third_parties supervisor ON c.supervisor_id = supervisor.id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (LOWER(c.numero_contrato) LIKE %s OR LOWER(c.objeto) LIKE %s OR LOWER(contratista.nombre) LIKE %s)"
            like_value = f"%{search.lower()}%"
            params.extend([like_value, like_value, like_value])

        if tipo:
            query += " AND c.tipo_contrato = %s"
            params.append(tipo)

        if estado == "activo":
            query += " AND c.activo = TRUE"
        elif estado == "inactivo":
            query += " AND c.activo = FALSE"

        query += " ORDER BY c.id DESC"

        cur.execute(query, params)
        contracts = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            "contracts.html",
            contracts=contracts,
            search=search,
            tipo=tipo,
            estado=estado
        )
    except Exception as e:
        return f"Error al listar contratos: {str(e)}"


@app.route("/contracts/new", methods=["GET", "POST"])
@login_required
def new_contract():
    try:
        create_contracts_table_if_needed()
        create_third_parties_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, nombre, tipo_tercero
            FROM third_parties
            WHERE estado = TRUE
            ORDER BY nombre
        """)
        third_parties = cur.fetchall()

        if request.method == "POST":
            numero_contrato = request.form.get("numero_contrato", "").strip()
            objeto = request.form.get("objeto", "").strip()
            tipo_contrato = request.form.get("tipo_contrato", "").strip()
            estado_contrato = request.form.get("estado_contrato", "").strip()
            valor_inicial = request.form.get("valor_inicial", "0").strip()
            valor_total = request.form.get("valor_total", "0").strip()
            fecha_suscripcion = request.form.get("fecha_suscripcion") or None
            fecha_inicio = request.form.get("fecha_inicio") or None
            fecha_fin = request.form.get("fecha_fin") or None
            contratista_id = request.form.get("contratista_id", "").strip()
            supervisor_id = request.form.get("supervisor_id") or None
            observaciones = request.form.get("observaciones", "").strip()

            errors = validate_contract_form(
                numero_contrato, objeto, tipo_contrato, estado_contrato,
                valor_inicial, valor_total, contratista_id
            )

            if errors:
                for error in errors:
                    flash(error, "error")
                contract = {
                    "numero_contrato": numero_contrato,
                    "objeto": objeto,
                    "tipo_contrato": tipo_contrato,
                    "estado_contrato": estado_contrato,
                    "valor_inicial": valor_inicial,
                    "valor_total": valor_total,
                    "fecha_suscripcion": fecha_suscripcion,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "contratista_id": int(contratista_id) if contratista_id else None,
                    "supervisor_id": int(supervisor_id) if supervisor_id else None,
                    "observaciones": observaciones,
                    "activo": True
                }
                cur.close()
                conn.close()
                return render_template(
                    "contract_form.html",
                    title="Nuevo Contrato",
                    contract=contract,
                    third_parties=third_parties,
                    is_edit=False
                )

            cur.execute("SELECT id FROM contracts WHERE numero_contrato = %s", (numero_contrato,))
            existing = cur.fetchone()

            if existing:
                flash("Ya existe un contrato con ese número.", "error")
                contract = {
                    "numero_contrato": numero_contrato,
                    "objeto": objeto,
                    "tipo_contrato": tipo_contrato,
                    "estado_contrato": estado_contrato,
                    "valor_inicial": valor_inicial,
                    "valor_total": valor_total,
                    "fecha_suscripcion": fecha_suscripcion,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "contratista_id": int(contratista_id) if contratista_id else None,
                    "supervisor_id": int(supervisor_id) if supervisor_id else None,
                    "observaciones": observaciones,
                    "activo": True
                }
                cur.close()
                conn.close()
                return render_template(
                    "contract_form.html",
                    title="Nuevo Contrato",
                    contract=contract,
                    third_parties=third_parties,
                    is_edit=False
                )

            cur.execute("""
                INSERT INTO contracts (
                    numero_contrato, objeto, tipo_contrato, estado_contrato,
                    valor_inicial, valor_total, fecha_suscripcion, fecha_inicio, fecha_fin,
                    contratista_id, supervisor_id, usuario_creador_id, observaciones, activo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """, (
                numero_contrato, objeto, tipo_contrato, estado_contrato,
                valor_inicial, valor_total, fecha_suscripcion, fecha_inicio, fecha_fin,
                contratista_id, supervisor_id if supervisor_id else None,
                session.get("user_id"), observaciones
            ))

            conn.commit()
            cur.close()
            conn.close()

            flash("Contrato creado correctamente.", "success")
            return redirect(url_for("list_contracts"))

        cur.close()
        conn.close()
        return render_template(
            "contract_form.html",
            title="Nuevo Contrato",
            contract=None,
            third_parties=third_parties,
            is_edit=False
        )

    except Exception as e:
        return f"Error al crear contrato: {str(e)}"


@app.route("/contracts/<int:contract_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contract(contract_id):
    try:
        create_contracts_table_if_needed()
        create_third_parties_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, nombre, tipo_tercero FROM third_parties WHERE estado = TRUE ORDER BY nombre")
        third_parties = cur.fetchall()

        cur.execute("SELECT * FROM contracts WHERE id = %s", (contract_id,))
        contract = cur.fetchone()

        if not contract:
            cur.close()
            conn.close()
            return "Contrato no encontrado."

        if request.method == "POST":
            numero_contrato = request.form.get("numero_contrato", "").strip()
            objeto = request.form.get("objeto", "").strip()
            tipo_contrato = request.form.get("tipo_contrato", "").strip()
            estado_contrato = request.form.get("estado_contrato", "").strip()
            valor_inicial = request.form.get("valor_inicial", "0").strip()
            valor_total = request.form.get("valor_total", "0").strip()
            fecha_suscripcion = request.form.get("fecha_suscripcion") or None
            fecha_inicio = request.form.get("fecha_inicio") or None
            fecha_fin = request.form.get("fecha_fin") or None
            contratista_id = request.form.get("contratista_id", "").strip()
            supervisor_id = request.form.get("supervisor_id") or None
            observaciones = request.form.get("observaciones", "").strip()
            activo_form = request.form.get("activo", "activo")
            activo_bool = True if activo_form == "activo" else False

            errors = validate_contract_form(
                numero_contrato, objeto, tipo_contrato, estado_contrato,
                valor_inicial, valor_total, contratista_id
            )

            if errors:
                for error in errors:
                    flash(error, "error")
                contract["numero_contrato"] = numero_contrato
                contract["objeto"] = objeto
                contract["tipo_contrato"] = tipo_contrato
                contract["estado_contrato"] = estado_contrato
                contract["valor_inicial"] = valor_inicial
                contract["valor_total"] = valor_total
                contract["fecha_suscripcion"] = fecha_suscripcion
                contract["fecha_inicio"] = fecha_inicio
                contract["fecha_fin"] = fecha_fin
                contract["contratista_id"] = int(contratista_id) if contratista_id else None
                contract["supervisor_id"] = int(supervisor_id) if supervisor_id else None
                contract["observaciones"] = observaciones
                contract["activo"] = activo_bool
                cur.close()
                conn.close()
                return render_template(
                    "contract_form.html",
                    title="Editar Contrato",
                    contract=contract,
                    third_parties=third_parties,
                    is_edit=True
                )

            cur.execute("SELECT id FROM contracts WHERE numero_contrato = %s AND id <> %s", (numero_contrato, contract_id))
            existing = cur.fetchone()

            if existing:
                flash("Ya existe otro contrato con ese número.", "error")
                contract["numero_contrato"] = numero_contrato
                contract["objeto"] = objeto
                contract["tipo_contrato"] = tipo_contrato
                contract["estado_contrato"] = estado_contrato
                contract["valor_inicial"] = valor_inicial
                contract["valor_total"] = valor_total
                contract["fecha_suscripcion"] = fecha_suscripcion
                contract["fecha_inicio"] = fecha_inicio
                contract["fecha_fin"] = fecha_fin
                contract["contratista_id"] = int(contratista_id) if contratista_id else None
                contract["supervisor_id"] = int(supervisor_id) if supervisor_id else None
                contract["observaciones"] = observaciones
                contract["activo"] = activo_bool
                cur.close()
                conn.close()
                return render_template(
                    "contract_form.html",
                    title="Editar Contrato",
                    contract=contract,
                    third_parties=third_parties,
                    is_edit=True
                )

            cur.execute("""
                UPDATE contracts
                SET numero_contrato = %s,
                    objeto = %s,
                    tipo_contrato = %s,
                    estado_contrato = %s,
                    valor_inicial = %s,
                    valor_total = %s,
                    fecha_suscripcion = %s,
                    fecha_inicio = %s,
                    fecha_fin = %s,
                    contratista_id = %s,
                    supervisor_id = %s,
                    observaciones = %s,
                    activo = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                numero_contrato, objeto, tipo_contrato, estado_contrato,
                valor_inicial, valor_total, fecha_suscripcion, fecha_inicio, fecha_fin,
                contratista_id, supervisor_id if supervisor_id else None,
                observaciones, activo_bool, contract_id
            ))

            conn.commit()
            cur.close()
            conn.close()

            flash("Contrato actualizado correctamente.", "success")
            return redirect(url_for("list_contracts"))

        cur.close()
        conn.close()
        return render_template(
            "contract_form.html",
            title="Editar Contrato",
            contract=contract,
            third_parties=third_parties,
            is_edit=True
        )

    except Exception as e:
        return f"Error al editar contrato: {str(e)}"


@app.route("/contracts/<int:contract_id>/toggle-status", methods=["POST"])
@login_required
def toggle_contract_status(contract_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, activo FROM contracts WHERE id = %s", (contract_id,))
        contract = cur.fetchone()

        if not contract:
            cur.close()
            conn.close()
            flash("Contrato no encontrado.", "error")
            return redirect(url_for("list_contracts"))

        new_status = not contract["activo"]

        cur.execute("""
            UPDATE contracts
            SET activo = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_status, contract_id))

        conn.commit()
        cur.close()
        conn.close()

        if new_status:
            flash("Contrato activado correctamente.", "success")
        else:
            flash("Contrato desactivado correctamente.", "success")

        return redirect(url_for("list_contracts"))

    except Exception as e:
        return f"Error al cambiar estado del contrato: {str(e)}"

@app.route("/contract-documents")
@login_required
def list_contract_documents():
    try:
        create_contracts_table_if_needed()
        create_contract_documents_table_if_needed()

        search = request.args.get("search", "").strip()
        tipo = request.args.get("tipo", "").strip()
        contract_id = request.args.get("contract_id", "").strip()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                cd.id,
                cd.contract_id,
                cd.tipo_documento,
                cd.titulo,
                cd.descripcion,
                cd.nombre_archivo_original,
                cd.version,
                cd.estado,
                cd.created_at,
                c.numero_contrato,
                tp.nombre AS contratista_nombre
            FROM contract_documents cd
            INNER JOIN contracts c ON cd.contract_id = c.id
            INNER JOIN third_parties tp ON c.contratista_id = tp.id
            WHERE 1=1
        """
        params = []

        if search:
            query += """
                AND (
                    LOWER(cd.titulo) LIKE %s
                    OR LOWER(cd.tipo_documento) LIKE %s
                    OR LOWER(c.numero_contrato) LIKE %s
                    OR LOWER(tp.nombre) LIKE %s
                )
            """
            like_value = f"%{search.lower()}%"
            params.extend([like_value, like_value, like_value, like_value])

        if tipo:
            query += " AND cd.tipo_documento = %s"
            params.append(tipo)

        if contract_id:
            query += " AND cd.contract_id = %s"
            params.append(contract_id)

        query += " ORDER BY cd.id DESC"

        cur.execute(query, params)
        documents = cur.fetchall()

        cur.execute("""
            SELECT id, numero_contrato
            FROM contracts
            WHERE activo = TRUE
            ORDER BY numero_contrato
        """)
        contracts = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            "contract_documents.html",
            documents=documents,
            contracts=contracts,
            search=search,
            tipo=tipo,
            contract_id=contract_id
        )
    except Exception as e:
        return f"Error al listar documentos contractuales: {str(e)}"


@app.route("/contract-documents/new", methods=["GET", "POST"])
@login_required
def new_contract_document():
    try:
        create_contracts_table_if_needed()
        create_contract_documents_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, numero_contrato
            FROM contracts
            WHERE activo = TRUE
            ORDER BY numero_contrato
        """)
        contracts = cur.fetchall()

        if request.method == "POST":
            contract_id = request.form.get("contract_id", "").strip()
            tipo_documento = request.form.get("tipo_documento", "").strip()
            titulo = request.form.get("titulo", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            version = request.form.get("version", "1.0").strip()
            estado = request.form.get("estado", "ACTIVO").strip()
            archivo = request.files.get("archivo")

            filename = archivo.filename if archivo and archivo.filename else None

            errors = validate_contract_document_form(
                contract_id, tipo_documento, titulo, filename, is_edit=False
            )

            if errors:
                for error in errors:
                    flash(error, "error")
                document = {
                    "contract_id": int(contract_id) if contract_id else None,
                    "tipo_documento": tipo_documento,
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "version": version,
                    "estado": estado
                }
                cur.close()
                conn.close()
                return render_template(
                    "contract_document_form.html",
                    title="Nuevo Documento Contractual",
                    document=document,
                    contracts=contracts,
                    is_edit=False
                )

            original_name = secure_filename(archivo.filename)
            extension = original_name.rsplit(".", 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)

            archivo.save(file_path)
            file_size = os.path.getsize(file_path)

            cur.execute("""
                INSERT INTO contract_documents (
                    contract_id,
                    tipo_documento,
                    titulo,
                    descripcion,
                    nombre_archivo_original,
                    nombre_archivo_guardado,
                    ruta_archivo,
                    extension_archivo,
                    tamano_archivo,
                    version,
                    estado,
                    usuario_cargue_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                contract_id,
                tipo_documento,
                titulo,
                descripcion,
                original_name,
                unique_name,
                file_path,
                extension,
                file_size,
                version,
                estado,
                session.get("user_id")
            ))

            conn.commit()
            cur.close()
            conn.close()

            flash("Documento contractual creado correctamente.", "success")
            return redirect(url_for("list_contract_documents"))

        cur.close()
        conn.close()
        return render_template(
            "contract_document_form.html",
            title="Nuevo Documento Contractual",
            document=None,
            contracts=contracts,
            is_edit=False
        )

    except Exception as e:
        return f"Error al crear documento contractual: {str(e)}"


@app.route("/contract-documents/<int:document_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contract_document(document_id):
    try:
        create_contracts_table_if_needed()
        create_contract_documents_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, numero_contrato
            FROM contracts
            WHERE activo = TRUE
            ORDER BY numero_contrato
        """)
        contracts = cur.fetchall()

        cur.execute("SELECT * FROM contract_documents WHERE id = %s", (document_id,))
        document = cur.fetchone()

        if not document:
            cur.close()
            conn.close()
            return "Documento contractual no encontrado."

        if request.method == "POST":
            contract_id = request.form.get("contract_id", "").strip()
            tipo_documento = request.form.get("tipo_documento", "").strip()
            titulo = request.form.get("titulo", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            version = request.form.get("version", "1.0").strip()
            estado = request.form.get("estado", "ACTIVO").strip()
            archivo = request.files.get("archivo")

            filename = archivo.filename if archivo and archivo.filename else None

            errors = validate_contract_document_form(
                contract_id, tipo_documento, titulo, filename, is_edit=True
            )

            if errors:
                for error in errors:
                    flash(error, "error")
                document["contract_id"] = int(contract_id) if contract_id else None
                document["tipo_documento"] = tipo_documento
                document["titulo"] = titulo
                document["descripcion"] = descripcion
                document["version"] = version
                document["estado"] = estado
                cur.close()
                conn.close()
                return render_template(
                    "contract_document_form.html",
                    title="Editar Documento Contractual",
                    document=document,
                    contracts=contracts,
                    is_edit=True
                )

            if archivo and archivo.filename:
                if document["ruta_archivo"] and os.path.exists(document["ruta_archivo"]):
                    os.remove(document["ruta_archivo"])

                original_name = secure_filename(archivo.filename)
                extension = original_name.rsplit(".", 1)[1].lower()
                unique_name = f"{uuid.uuid4().hex}.{extension}"
                file_path = os.path.join(UPLOAD_DIR, unique_name)

                archivo.save(file_path)
                file_size = os.path.getsize(file_path)

                cur.execute("""
                    UPDATE contract_documents
                    SET contract_id = %s,
                        tipo_documento = %s,
                        titulo = %s,
                        descripcion = %s,
                        nombre_archivo_original = %s,
                        nombre_archivo_guardado = %s,
                        ruta_archivo = %s,
                        extension_archivo = %s,
                        tamano_archivo = %s,
                        version = %s,
                        estado = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    contract_id,
                    tipo_documento,
                    titulo,
                    descripcion,
                    original_name,
                    unique_name,
                    file_path,
                    extension,
                    file_size,
                    version,
                    estado,
                    document_id
                ))
            else:
                cur.execute("""
                    UPDATE contract_documents
                    SET contract_id = %s,
                        tipo_documento = %s,
                        titulo = %s,
                        descripcion = %s,
                        version = %s,
                        estado = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    contract_id,
                    tipo_documento,
                    titulo,
                    descripcion,
                    version,
                    estado,
                    document_id
                ))

            conn.commit()
            cur.close()
            conn.close()

            flash("Documento contractual actualizado correctamente.", "success")
            return redirect(url_for("list_contract_documents"))

        cur.close()
        conn.close()
        return render_template(
            "contract_document_form.html",
            title="Editar Documento Contractual",
            document=document,
            contracts=contracts,
            is_edit=True
        )

    except Exception as e:
        return f"Error al editar documento contractual: {str(e)}"


@app.route("/contract-documents/<int:document_id>/download")
@login_required
def download_contract_document(document_id):
    try:
        create_contract_documents_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT nombre_archivo_original, ruta_archivo
            FROM contract_documents
            WHERE id = %s
        """, (document_id,))
        document = cur.fetchone()

        cur.close()
        conn.close()

        if not document:
            return "Documento no encontrado."

        if not os.path.exists(document["ruta_archivo"]):
            return "El archivo no existe en el servidor."

        return send_file(
            document["ruta_archivo"],
            as_attachment=True,
            download_name=document["nombre_archivo_original"]
        )

    except Exception as e:
        return f"Error al descargar documento contractual: {str(e)}"


@app.route("/contract-documents/<int:document_id>/delete", methods=["POST"])
@login_required
def delete_contract_document(document_id):
    try:
        create_contract_documents_table_if_needed()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT ruta_archivo FROM contract_documents WHERE id = %s", (document_id,))
        document = cur.fetchone()

        if not document:
            cur.close()
            conn.close()
            flash("Documento contractual no encontrado.", "error")
            return redirect(url_for("list_contract_documents"))

        if document["ruta_archivo"] and os.path.exists(document["ruta_archivo"]):
            os.remove(document["ruta_archivo"])

        cur.execute("DELETE FROM contract_documents WHERE id = %s", (document_id,))
        conn.commit()

        cur.close()
        conn.close()

        flash("Documento contractual eliminado correctamente.", "success")
        return redirect(url_for("list_contract_documents"))

    except Exception as e:
        return f"Error al eliminar documento contractual: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
