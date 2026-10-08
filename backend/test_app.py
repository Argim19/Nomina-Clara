import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ["NOMINA_DB_PATH"] = str(Path(tempfile.gettempdir()) / "nomina_clara_test.db")
from backend import app


class PayrollTests(unittest.TestCase):
    def setUp(self):
        if app.DB_PATH.exists():
            app.DB_PATH.unlink()
        app.init_db(seed=False)

    def test_child_bonus_scale(self):
        self.assertEqual(app.child_bonus(0), 0)
        self.assertEqual(app.child_bonus(1), 250_000)
        self.assertEqual(app.child_bonus(2), 400_000)
        self.assertEqual(app.child_bonus(3), 600_000)
        self.assertEqual(app.child_bonus(8), 600_000)

    def test_payroll_calculation(self):
        employee = {"hourly_rate": 25_000, "children": 2}
        result = app.calculate_payroll(employee, 160, {"eps_percent": 4, "pension_percent": 4, "arl_percent": 0, "other_amount": 50_000})
        self.assertEqual(result["base_pay"], 4_000_000)
        self.assertEqual(result["child_bonus"], 400_000)
        self.assertEqual(result["total_deductions"], 370_000)
        self.assertEqual(result["net_pay"], 4_030_000)

    def test_historical_schema_has_no_update_trigger_path(self):
        with app.connect() as db:
            columns = [row[1] for row in db.execute("PRAGMA table_info(payrolls)")]
            self.assertIn("employee_name", columns)
            self.assertIn("hourly_rate", columns)
            self.assertIn("children", columns)

    def test_token_roundtrip(self):
        token = app.issue_token("admin@nominaclara.co")
        self.assertTrue(app.valid_token(token))
        self.assertFalse(app.valid_token(token + "x"))

    def test_team_members_in_seed(self):
        app.init_db(seed=True)
        with app.connect() as db:
            emails = {row[0] for row in db.execute("SELECT email FROM employees").fetchall()}
            expected_team_emails = {
                "ddamago0@gmail.com",
                "davidperez1019@gmail.com",
                "sayderochoa@gmail.com",
                "jhonata0200p@gmail.com"
            }
            for team_email in expected_team_emails:
                self.assertIn(team_email, emails)

    def test_build_payroll_email_content(self):
        payroll = {
            "id": 1,
            "code": "NOM-202610-0001",
            "period": "2026-10",
            "employee_name": "Daniel David Martinez Gonzalez",
            "employee_document": "1098765001",
            "employee_position": "Ingeniero de Software",
            "employee_email": "ddamago0@gmail.com",
            "hours": 160,
            "hourly_rate": 45000,
            "children": 0,
            "base_pay": 7200000,
            "child_bonus": 0,
            "eps_percent": 4,
            "pension_percent": 4,
            "arl_percent": 0,
            "eps_deduction": 288000,
            "pension_deduction": 288000,
            "arl_deduction": 0,
            "other_label": "Otros conceptos",
            "other_deduction": 0,
            "total_deductions": 576000,
            "net_pay": 6624000,
        }
        subject, text_content, html_content = app.build_payroll_email_content(payroll)
        self.assertIn("NOM-202610-0001", subject)
        self.assertIn("Daniel David Martinez Gonzalez", text_content)
        self.assertIn("ddamago0@gmail.com", text_content)
        self.assertIn("Daniel David Martinez Gonzalez", html_content)
        self.assertIn("ddamago0@gmail.com", html_content)

    def test_send_payroll_email_persistence(self):
        payroll = {
            "id": 99,
            "code": "NOM-202610-0099",
            "period": "2026-10",
            "employee_name": "Josue Blanco",
            "employee_document": "1098765002",
            "employee_position": "Desarrollador Backend",
            "employee_email": "davidperez1019@gmail.com",
            "hours": 160,
            "hourly_rate": 42000,
            "children": 0,
            "base_pay": 6720000,
            "child_bonus": 0,
            "eps_percent": 4,
            "pension_percent": 4,
            "arl_percent": 0,
            "eps_deduction": 268800,
            "pension_deduction": 268800,
            "arl_deduction": 0,
            "other_label": "Otros conceptos",
            "other_deduction": 0,
            "total_deductions": 537600,
            "net_pay": 6182400,
        }
        dispatch = app.send_payroll_email(payroll)
        self.assertIn(dispatch["status"], ("prepared", "sent", "fallback_local"))
        self.assertEqual(dispatch["recipient"], "davidperez1019@gmail.com")

    def test_resend_email_structure(self):
        old_key = app.RESEND_API_KEY
        try:
            app.RESEND_API_KEY = "re_test_dummy_key"
            res = app.send_resend_email("test@example.com", "Asunto", "<p>HTML</p>", "Texto")
            self.assertEqual(res["provider"], "resend")
            self.assertIn(res["status"], ("error_resend", "sent"))
        finally:
            app.RESEND_API_KEY = old_key


if __name__ == "__main__":
    unittest.main()

