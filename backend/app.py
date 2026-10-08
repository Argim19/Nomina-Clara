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

ENV_PATH = BASE_DIR.parent / ".env"
if ENV_PATH.exists():
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))

SMTP_HOST = os.environ.get("NOMINA_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("NOMINA_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("NOMINA_SMTP_USER", "ddamago0@gmail.com")
SMTP_PASSWORD = os.environ.get("NOMINA_SMTP_PASSWORD", "").replace(" ", "")
SMTP_FROM = os.environ.get("NOMINA_SMTP_FROM", os.environ.get("NOMINA_SMTP_USER", "ddamago0@gmail.com"))
SMTP_TLS = os.environ.get("NOMINA_SMTP_TLS", "true").lower() == "true"

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "Nómina Clara <onboarding@resend.dev>")


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
        if seed:
            now = utc_now()
            team_and_demo = [
                ("Daniel David Martinez Gonzalez", "1098765001", "Bogotá", "ddamago0@gmail.com", "310 123 4567", "Ingeniero de Software", 45000, 0, "Activo", now, now),
                ("Josue Blanco", "1098765002", "Medellín", "davidperez1019@gmail.com", "315 234 5678", "Desarrollador Backend", 42000, 0, "Activo", now, now),
                ("Sayder Carreño", "1098765003", "Cali", "sayderochoa@gmail.com", "300 345 6789", "Desarrollador Frontend", 42000, 0, "Activo", now, now),
                ("Jhonatan Miranda", "1098765004", "Barranquilla", "jhonata0200p@gmail.com", "316 456 7890", "Analista de Sistemas", 40000, 0, "Activo", now, now),
                ("Valentina Rojas Martínez", "1032456789", "Bogotá", "valentina.rojas@empresa.co", "310 482 7615", "Coordinadora administrativa", 42000, 2, "Activo", now, now),
                ("Andrés Felipe Moreno", "1018456723", "Medellín", "andres.moreno@empresa.co", "315 704 2298", "Analista financiero", 36500, 1, "Activo", now, now),
                ("Laura Camila Torres", "1144098765", "Cali", "laura.torres@empresa.co", "300 651 9042", "Líder de operaciones", 48000, 0, "Activo", now, now),
                ("Santiago Vélez Ospina", "98765432", "Pereira", "santiago.velez@empresa.co", "316 820 1173", "Auxiliar logístico", 24500, 3, "Inactivo", now, now),
            ]
            for emp in team_and_demo:
                db.execute("""INSERT OR IGNORE INTO employees(name, document, city, email, phone, position, hourly_rate, children, status, created_at, updated_at)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?)""", emp)


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


def format_currency(value):
    val = float(value or 0)
    int_part = f"{int(val):,}".replace(",", ".")
    dec_part = f"{val:.2f}".split(".")[1]
    return f"${int_part},{dec_part}"


def build_payroll_email_content(payroll):
    code = payroll.get("code") or f"NOM-{payroll.get('id', 0):04d}"
    period = payroll.get("period", "")
    emp_name = payroll.get("employee_name", "")
    emp_doc = payroll.get("employee_document", "")
    emp_pos = payroll.get("employee_position", "")
    emp_email = payroll.get("employee_email", "")
    hours = payroll.get("hours", 0)
    rate = payroll.get("hourly_rate", 0)
    base_pay = payroll.get("base_pay", 0)
    child_bonus_val = payroll.get("child_bonus", 0)
    children = payroll.get("children", 0)
    eps_ded = payroll.get("eps_deduction", 0)
    pension_ded = payroll.get("pension_deduction", 0)
    arl_ded = payroll.get("arl_deduction", 0)
    eps_pct = payroll.get("eps_percent", 0)
    pension_pct = payroll.get("pension_percent", 0)
    arl_pct = payroll.get("arl_percent", 0)
    other_label = payroll.get("other_label") or "Otros conceptos"
    other_ded = payroll.get("other_deduction", 0)
    total_ded = payroll.get("total_deductions", 0)
    net_pay = payroll.get("net_pay", 0)
    total_dev = base_pay + child_bonus_val

    subject = f"[Nómina Clara] Comprobante de pago de nómina - {code} ({period})"

    text_content = f"""NÓMINA CLARA - COMPROBANTE DE PAGO
============================================================
Liquidación: {code}
Periodo liquidado: {period}

DATOS DEL EMPLEADO
------------------------------------------------------------
Nombre: {emp_name}
Documento: CC {emp_doc}
Cargo: {emp_pos}
Correo: {emp_email}
Horas liquidadas: {hours} h (Tarifa: {format_currency(rate)}/h)
Hijos registrados: {children}

DEVENGADOS
------------------------------------------------------------
- Pago por horas ({hours}h): {format_currency(base_pay)}
- Bonificación por hijos ({children} reg.): {format_currency(child_bonus_val)}
Total Devengado: {format_currency(total_dev)}

DEDUCCIONES
------------------------------------------------------------
- EPS ({eps_pct}%): - {format_currency(eps_ded)}
- Pensión ({pension_pct}%): - {format_currency(pension_ded)}
- ARL ({arl_pct}%): - {format_currency(arl_ded)}
{f'- {other_label}: - {format_currency(other_ded)}' if other_ded > 0 else ''}
Total Deducciones: - {format_currency(total_ded)}

============================================================
NETO A PAGAR: {format_currency(net_pay)}
============================================================

Este comprobante corresponde a una liquidación cerrada emitida por el sistema Nómina Clara.
"""

    other_row = f"<tr><td>{other_label}</td><td class='amount deduction'>- {format_currency(other_ded)}</td></tr>" if other_ded > 0 else ""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 24px 28px; display: flex; justify-content: space-between; align-items: center; }}
    .logo {{ font-size: 20px; font-weight: 800; letter-spacing: -0.5px; color: #ffffff; }}
    .logo span {{ color: #38bdf8; font-weight: 400; }}
    .code-badge {{ background: rgba(255, 255, 255, 0.15); padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; border: 1px solid rgba(255, 255, 255, 0.2); color: #ffffff; }}
    .content {{ padding: 28px; }}
    .intro {{ margin-bottom: 22px; }}
    .intro h2 {{ margin: 0 0 6px 0; font-size: 20px; color: #0f172a; }}
    .intro p {{ margin: 0; color: #64748b; font-size: 14px; }}
    .info-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 18px; margin-bottom: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .info-item small {{ display: block; color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 600; margin-bottom: 2px; }}
    .info-item strong {{ font-size: 14px; color: #0f172a; }}
    .table-container {{ margin-bottom: 24px; }}
    .table-title {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; color: #475569; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 14px; }}
    th {{ background: #f1f5f9; padding: 8px 12px; text-align: left; font-size: 12px; color: #475569; font-weight: 600; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #f1f5f9; }}
    td.amount {{ text-align: right; font-weight: 600; }}
    .deduction {{ color: #dc2626; }}
    .earning {{ color: #0f172a; }}
    .net-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 18px 22px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
    .net-box .label {{ font-size: 14px; font-weight: 600; color: #166534; }}
    .net-box .value {{ font-size: 22px; font-weight: 800; color: #15803d; }}
    .footer {{ border-top: 1px solid #e2e8f0; padding: 16px 28px; background: #fafafa; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">NÓMINA <span>CLARA</span></div>
      <div class="code-badge">{code}</div>
    </div>
    <div class="content">
      <div class="intro">
        <h2>Comprobante de Pago de Nómina</h2>
        <p>A continuación se detalla la liquidación correspondiente al periodo <strong>{period}</strong>.</p>
      </div>

      <div class="info-card">
        <div class="info-item">
          <small>Empleado</small>
          <strong>{emp_name}</strong>
          <span style="display: block; color: #64748b; font-size: 12px;">{emp_email}</span>
        </div>
        <div class="info-item">
          <small>Documento</small>
          <strong>CC {emp_doc}</strong>
        </div>
        <div class="info-item">
          <small>Cargo</small>
          <strong>{emp_pos}</strong>
        </div>
        <div class="info-item">
          <small>Horas Liquidadas</small>
          <strong>{hours} h ({format_currency(rate)}/h)</strong>
        </div>
      </div>

      <div class="table-container">
        <div class="table-title">Devengados</div>
        <table>
          <tr><th>Concepto</th><th style="text-align: right;">Valor</th></tr>
          <tr><td>Pago por horas trabajadas ({hours} h)</td><td class="amount earning">{format_currency(base_pay)}</td></tr>
          <tr><td>Bonificación por hijos ({children} reg.)</td><td class="amount earning">{format_currency(child_bonus_val)}</td></tr>
          <tr style="background: #fafafa;"><td><strong>Total Devengado</strong></td><td class="amount earning"><strong>{format_currency(total_dev)}</strong></td></tr>
        </table>

        <div class="table-title">Deducciones</div>
        <table>
          <tr><th>Concepto</th><th style="text-align: right;">Valor</th></tr>
          <tr><td>EPS ({eps_pct}%)</td><td class="amount deduction">- {format_currency(eps_ded)}</td></tr>
          <tr><td>Pensión ({pension_pct}%)</td><td class="amount deduction">- {format_currency(pension_ded)}</td></tr>
          <tr><td>ARL ({arl_pct}%)</td><td class="amount deduction">- {format_currency(arl_ded)}</td></tr>
          {other_row}
          <tr style="background: #fafafa;"><td><strong>Total Deducciones</strong></td><td class="amount deduction"><strong>- {format_currency(total_ded)}</strong></td></tr>
        </table>
      </div>

      <div class="net-box">
        <div>
          <div class="label">Neto Pagado</div>
          <small style="color: #64748b; font-size: 12px;">Valor transferido a cuenta</small>
        </div>
        <div class="value">{format_currency(net_pay)}</div>
      </div>
    </div>
    <div class="footer">
      Este comprobante corresponde a una liquidación inmutable registrada en Nómina Clara.<br>
      © 2026 Nómina Clara · Gestión laboral transparente
    </div>
  </div>
</body>
</html>
"""
    return subject, text_content, html_content


def send_payroll_email(payroll):
    recipient = payroll.get("employee_email")
    if not recipient:
        return {"status": "error", "message": "El empleado no tiene correo registrado."}

    subject, text_content, html_content = build_payroll_email_content(payroll)

    emails_dir = DATA_DIR / "emails"
    emails_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    code_safe = (payroll.get("code") or "NOM").replace("/", "_").replace("-", "_")
    email_file = emails_dir / f"{code_safe}_{timestamp}.json"

    try:
        with open(email_file, "w", encoding="utf-8") as f:
            json.dump({
                "to": recipient,
                "subject": subject,
                "sent_at": utc_now(),
                "payroll_code": payroll.get("code"),
                "text": text_content,
                "html": html_content
            }, f, ensure_ascii=False, indent=2)
    except Exception as err:
        print("Error al guardar copia local del correo:", err)

    # 1. Despacho por Resend si está configurado
    if RESEND_API_KEY:
        resend_result = send_resend_email(recipient, subject, html_content, text_content)
        if resend_result.get("status") == "sent":
            return resend_result
        if not (SMTP_USER and SMTP_PASSWORD):
            return resend_result
        print(f"Resend falló ({resend_result.get('message')}), procediendo con respaldo SMTP...")

    # 2. Despacho por SMTP
    if not SMTP_USER or not SMTP_PASSWORD:
        return {
            "status": "prepared",
            "recipient": recipient,
            "message": f"Comprobante registrado y respaldado para {recipient}. Configure RESEND_API_KEY o NOMINA_SMTP_USER.",
            "file": str(email_file.name)
        }

    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = recipient
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            if SMTP_TLS:
                server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM or SMTP_USER, [recipient], msg.as_string())
        server.quit()
        return {
            "status": "sent",
            "provider": "smtp",
            "recipient": recipient,
            "message": f"Comprobante enviado exitosamente por correo a {recipient}."
        }
    except Exception as exc:
        print(f"Error al enviar correo SMTP a {recipient}: {exc}")
        return {
            "status": "fallback_local",
            "recipient": recipient,
            "message": f"No se pudo enviar el correo vía SMTP ({exc}). El comprobante quedó guardado en el sistema.",
            "file": str(email_file.name)
        }


def send_resend_email(recipient, subject, html_content, text_content):
    import urllib.request
    import urllib.error

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "NominaClara/1.0"
    }
    payload = {
        "from": RESEND_FROM,
        "to": [recipient],
        "subject": subject,
        "html": html_content,
        "text": text_content
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return {
                "status": "sent",
                "provider": "resend",
                "recipient": recipient,
                "message": f"Comprobante enviado exitosamente vía Resend a {recipient}.",
                "id": res_body.get("id")
            }
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode("utf-8")
        print(f"Error Resend HTTP {err.code}: {err_msg}")
        return {
            "status": "error_resend",
            "provider": "resend",
            "recipient": recipient,
            "message": f"Error de Resend ({err.code}): {err_msg}"
        }
    except Exception as exc:
        print(f"Error Resend: {exc}")
        return {
            "status": "error_resend",
            "provider": "resend",
            "recipient": recipient,
            "message": f"Fallo al conectar con Resend: {exc}"
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
            payroll_dict = as_dict(row)
        email_dispatch = send_payroll_email(payroll_dict)
        payroll_dict["email_dispatch"] = email_dispatch
        self.send_json(201, payroll_dict)

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
            row = db.execute("SELECT * FROM payrolls WHERE id = ?", (payroll_id,)).fetchone()
        if not row: return self.send_json(404, {"error": "La liquidación no existe."})
        result = send_payroll_email(as_dict(row))
        self.send_json(200, result)


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

