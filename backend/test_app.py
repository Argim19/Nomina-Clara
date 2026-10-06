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


if __name__ == "__main__":
    unittest.main()

