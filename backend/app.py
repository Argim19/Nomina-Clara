#!/usr/bin/env python3
"""API local de Nómina Clara. Solo usa la biblioteca estándar de Python."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("NOMINA_DB_PATH", DATA_DIR / "nomina.db"))
HOST = os.environ.get("NOMINA_HOST", "0.0.0.0")
PORT = int(os.environ.get("NOMINA_PORT", "8000"))
ADMIN_EMAIL = os.environ.get("NOMINA_ADMIN_EMAIL", "admin@nominaclara.co")
ADMIN_PASSWORD = os.environ.get("NOMINA_ADMIN_PASSWORD", "Nomina2026!")
TOKEN_SECRET = os.environ.get("NOMINA_TOKEN_SECRET", secrets.token_hex(32))
ALLOWED_ORIGIN = os.environ.get("NOMINA_ALLOWED_ORIGIN", "http://localhost:5173")


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(seed=True):
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            document TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            position TEXT NOT NULL,
            hourly_rate REAL NOT NULL CHECK(hourly_rate > 0),
            children INTEGER NOT NULL DEFAULT 0 CHECK(children >= 0),
            status TEXT NOT NULL DEFAULT 'Activo' CHECK(status IN ('Activo', 'Inactivo')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS payrolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            employee_id INTEGER NOT NULL,
            employee_name TEXT NOT NULL,
            employee_document TEXT NOT NULL,
            employee_email TEXT NOT NULL,
            employee_position TEXT NOT NULL,
            hourly_rate REAL NOT NULL,
            children INTEGER NOT NULL,
            period TEXT NOT NULL,
            hours REAL NOT NULL CHECK(hours > 0),
            base_pay REAL NOT NULL,
            child_bonus REAL NOT NULL,
            eps_percent REAL NOT NULL,
            pension_percent REAL NOT NULL,
            arl_percent REAL NOT NULL,
            eps_deduction REAL NOT NULL,
            pension_deduction REAL NOT NULL,
            arl_deduction REAL NOT NULL,
            other_label TEXT NOT NULL,
            other_deduction REAL NOT NULL,
            total_deductions REAL NOT NULL,
            net_pay REAL NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(employee_id, period),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        defaults = {"eps_percent": "4", "pension_percent": "4", "arl_percent": "0"}
        for key, value in defaults.items():
            db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (key, value))
        if seed and db.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
            now = utc_now()
            employees = [
                ("Valentina Rojas Martínez", "1032456789", "Bogotá", "valentina.rojas@empresa.co", "310 482 7615", "Coordinadora administrativa", 42000, 2, "Activo", now, now),
                ("Andrés Felipe Moreno", "1018456723", "Medellín", "andres.moreno@empresa.co", "315 704 2298", "Analista financiero", 36500, 1, "Activo", now, now),
                ("Laura Camila Torres", "1144098765", "Cali", "laura.torres@empresa.co", "300 651 9042", "Líder de operaciones", 48000, 0, "Activo", now, now),
                ("Santiago Vélez Ospina", "98765432", "Pereira", "santiago.velez@empresa.co", "316 820 1173", "Auxiliar logístico", 24500, 3, "Inactivo", now, now),
            ]
            db.executemany("""INSERT INTO employees(name, document, city, email, phone, position, hourly_rate, children, status, created_at, updated_at)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?)""", employees)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def child_bonus(children):
    if children >= 3:
        return 600_000
    if children == 2:
        return 400_000
    if children == 1:
        return 250_000
    return 0


def calculate_payroll(employee, hours, deductions):
    base = round(float(employee["hourly_rate"]) * hours, 2)
    bonus = child_bonus(int(employee["children"]))
    eps_percent = float(deductions.get("eps_percent", 4))
    pension_percent = float(deductions.get("pension_percent", 4))
    arl_percent = float(deductions.get("arl_percent", 0))
    other = float(deductions.get("other_amount", 0) or 0)
    if min(eps_percent, pension_percent, arl_percent, other) < 0:
        raise ValueError("Los valores de deducción no pueden ser negativos.")
    eps = round(base * eps_percent / 100, 2)
    pension = round(base * pension_percent / 100, 2)
    arl = round(base * arl_percent / 100, 2)
    total = round(eps + pension + arl + other, 2)
    net = round(base + bonus - total, 2)
    if net < 0:
        raise ValueError("Las deducciones superan el valor devengado.")
    return {
        "base_pay": base, "child_bonus": bonus,
        "eps_percent": eps_percent, "pension_percent": pension_percent, "arl_percent": arl_percent,
        "eps_deduction": eps, "pension_deduction": pension, "arl_deduction": arl,
        "other_label": str(deductions.get("other_label", "Otros conceptos"))[:80],
        "other_deduction": other, "total_deductions": total, "net_pay": net,
    }


def issue_token(email):
    expires = int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp())
    payload = f"{email}|{expires}"
    signature = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def valid_token(token):
    try:
        email, expires, signature = token.rsplit("|", 2)
        expected = hmac.new(TOKEN_SECRET.encode(), f"{email}|{expires}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected) and int(expires) > int(datetime.now(timezone.utc).timestamp())
    except (ValueError, TypeError):
        return False


def as_dict(row):
    return dict(row) if row else None


def validate_employee(data):
    required = ["name", "document", "city", "email", "phone", "position", "hourly_rate", "children", "status"]
    missing = [field for field in required if data.get(field) in (None, "")]
    if missing:
        raise ValueError("Complete todos los campos obligatorios.")
    if "@" not in str(data["email"]):
        raise ValueError("Ingrese un correo electrónico válido.")
    if float(data["hourly_rate"]) <= 0 or int(data["children"]) < 0:
        raise ValueError("Revise el valor por hora y el número de hijos.")
    if data["status"] not in ("Activo", "Inactivo"):
        raise ValueError("El estado seleccionado no es válido.")
    return (
        str(data["name"]).strip(), str(data["document"]).strip(), str(data["city"]).strip(),
        str(data["email"]).strip().lower(), str(data["phone"]).strip(), str(data["position"]).strip(),
        float(data["hourly_rate"]), int(data["children"]), data["status"],
    )


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "NominaClara/1.0"

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def end_headers(self):
        origin = self.headers.get("Origin", "")
        allowed = origin if origin in {ALLOWED_ORIGIN, "http://127.0.0.1:5173"} else ALLOWED_ORIGIN
        self.send_header("Access-Control-Allow-Origin", allowed)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Vary", "Origin")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            raise ValueError("La solicitud no contiene información válida.")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        header = self.headers.get("Authorization", "")
        return header.startswith("Bearer ") and valid_token(header[7:])

    def route(self, method):
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            if path == "/api/health" and method == "GET":
                return self.send_json(200, {"status": "ok", "service": "Nómina Clara API"})
            if path == "/api/auth/login" and method == "POST":
                return self.login()
            if not self.authorized():
                return self.send_json(401, {"error": "Su sesión no es válida. Ingrese nuevamente."})
            if path == "/api/employees" and method == "GET": return self.list_employees()
            if path == "/api/employees" and method == "POST": return self.create_employee()
            if path.startswith("/api/employees/") and method == "PUT": return self.update_employee(int(path.rsplit("/", 1)[1]))
            if path == "/api/payrolls" and method == "GET": return self.list_payrolls()
            if path == "/api/payrolls" and method == "POST": return self.create_payroll()
            if path.startswith("/api/payrolls/") and path.endswith("/email") and method == "POST": return self.prepare_email(int(path.split("/")[3]))
            if path == "/api/config/deductions" and method == "GET": return self.get_deductions()
            if path == "/api/dashboard" and method == "GET": return self.dashboard()
            return self.send_json(404, {"error": "El recurso solicitado no existe."})
        except ValueError as exc:
            return self.send_json(400, {"error": str(exc)})
        except sqlite3.IntegrityError as exc:
            message = "Ya existe un registro con esa información."
            if "employees.document" in str(exc): message = "Ya existe un empleado con esa cédula."
            if "employees.email" in str(exc): message = "Ya existe un empleado con ese correo."
            if "payrolls.employee_id" in str(exc): message = "Este empleado ya tiene una liquidación registrada para el periodo seleccionado."
            return self.send_json(409, {"error": message})
        except Exception as exc:
            print("API error:", repr(exc))
            return self.send_json(500, {"error": "Ocurrió un error interno. Intente nuevamente."})

    def login(self):
        data = self.json_body()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        valid_email = hmac.compare_digest(email, ADMIN_EMAIL.lower())
        valid_password = hmac.compare_digest(password, ADMIN_PASSWORD)
        if not (valid_email and valid_password):
            return self.send_json(401, {"error": "El correo o la contraseña no coinciden."})
        return self.send_json(200, {"token": issue_token(email), "user": {"name": "Catalina Gómez", "role": "Administradora de nómina", "email": email}})

    def list_employees(self):
        with connect() as db:
            rows = db.execute("SELECT * FROM employees ORDER BY status ASC, name ASC").fetchall()
        self.send_json(200, [as_dict(row) for row in rows])

    def create_employee(self):
        values = validate_employee(self.json_body())
        now = utc_now()
        with connect() as db:
            cursor = db.execute("""INSERT INTO employees(name, document, city, email, phone, position, hourly_rate, children, status, created_at, updated_at)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (*values, now, now))
            row = db.execute("SELECT * FROM employees WHERE id = ?", (cursor.lastrowid,)).fetchone()
        self.send_json(201, as_dict(row))

    def update_employee(self, employee_id):
        values = validate_employee(self.json_body())
        with connect() as db:
            if not db.execute("SELECT 1 FROM employees WHERE id = ?", (employee_id,)).fetchone():
                return self.send_json(404, {"error": "El empleado no existe."})
            db.execute("""UPDATE employees SET name=?, document=?, city=?, email=?, phone=?, position=?, hourly_rate=?, children=?, status=?, updated_at=? WHERE id=?""", (*values, utc_now(), employee_id))
            row = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        self.send_json(200, as_dict(row))

    def list_payrolls(self):
        with connect() as db:
            rows = db.execute("SELECT * FROM payrolls ORDER BY created_at DESC, id DESC").fetchall()
        self.send_json(200, [as_dict(row) for row in rows])

    def create_payroll(self):
        data = self.json_body()
        try:
            employee_id, hours = int(data.get("employee_id")), float(data.get("hours"))
        except (TypeError, ValueError):
            raise ValueError("Seleccione un empleado e ingrese las horas trabajadas.")
        period = str(data.get("period", ""))
        if len(period) != 7 or period[4] != "-": raise ValueError("Seleccione un periodo válido.")
        if hours <= 0 or hours > 744: raise ValueError("Las horas deben estar entre 1 y 744.")
        with connect() as db:
            employee = db.execute("SELECT * FROM employees WHERE id = ? AND status = 'Activo'", (employee_id,)).fetchone()
            if not employee: raise ValueError("El empleado no existe o se encuentra inactivo.")
            calc = calculate_payroll(employee, hours, data.get("deductions", {}))
            now = utc_now()
            cursor = db.execute("""INSERT INTO payrolls(employee_id, employee_name, employee_document, employee_email, employee_position,
                hourly_rate, children, period, hours, base_pay, child_bonus, eps_percent, pension_percent, arl_percent,
                eps_deduction, pension_deduction, arl_deduction, other_label, other_deduction, total_deductions, net_pay, created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (employee_id, employee["name"], employee["document"], employee["email"], employee["position"], employee["hourly_rate"], employee["children"], period, hours,
                 calc["base_pay"], calc["child_bonus"], calc["eps_percent"], calc["pension_percent"], calc["arl_percent"], calc["eps_deduction"], calc["pension_deduction"], calc["arl_deduction"], calc["other_label"], calc["other_deduction"], calc["total_deductions"], calc["net_pay"], now))
            payroll_id = cursor.lastrowid
            code = f"NOM-{period.replace('-', '')}-{payroll_id:04d}"
            db.execute("UPDATE payrolls SET code = ? WHERE id = ?", (code, payroll_id))
            row = db.execute("SELECT * FROM payrolls WHERE id = ?", (payroll_id,)).fetchone()
        self.send_json(201, as_dict(row))

    def get_deductions(self):
        with connect() as db:
            rows = db.execute("SELECT key, value FROM settings").fetchall()
        self.send_json(200, {row["key"]: float(row["value"]) for row in rows})

    def dashboard(self):
        current_period = datetime.now().strftime("%Y-%m")
        with connect() as db:
            totals = db.execute("SELECT COUNT(*) total, SUM(status='Activo') active FROM employees").fetchone()
            payroll = db.execute("SELECT COUNT(*) count, COALESCE(SUM(CASE WHEN period=? THEN net_pay ELSE 0 END), 0) current FROM payrolls", (current_period,)).fetchone()
            recent = db.execute("SELECT id, employee_name, period, hours, net_pay, created_at FROM payrolls ORDER BY created_at DESC LIMIT 4").fetchall()
        self.send_json(200, {"total_employees": totals["total"], "active_employees": totals["active"] or 0, "payroll_count": payroll["count"], "current_payroll": payroll["current"], "current_period": current_period, "recent_payrolls": [as_dict(r) for r in recent]})

    def prepare_email(self, payroll_id):
        with connect() as db:
            row = db.execute("SELECT employee_email FROM payrolls WHERE id = ?", (payroll_id,)).fetchone()
        if not row: return self.send_json(404, {"error": "La liquidación no existe."})
        self.send_json(200, {"status": "prepared", "recipient": row["employee_email"], "message": f"Correo preparado para {row['employee_email']}. Configure un proveedor SMTP para habilitar el envío."})


def run():
    init_db(seed=os.environ.get("NOMINA_SEED_DEMO", "true").lower() == "true")
    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"Nómina Clara API disponible en http://localhost:{PORT}")
    print(f"Acceso local: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    run()

