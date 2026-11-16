import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pos.application.facade import PosFacade
from pos.bootstrap import create_container
from pos.domain.model import ValidationError


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.app = create_container(self.base / "pos.json").resolve("facade")
        self.assertIsInstance(self.app, PosFacade)

    def test_full_scenario_and_csv_export(self):
        student = self.app.add_student("Анна")
        criterion = self.app.add_criterion("Экзамен", "100", "1")
        self.app.set_evaluation(student.id, criterion.id, "85", "Хорошо")
        self.assertEqual(self.app.total(student.id).score10, Decimal("8.50"))
        path = self.base / "output" / "grades.csv"
        self.assertEqual(self.app.export_report(path), 1)
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            records = list(csv.reader(stream))
        self.assertEqual(records[0][2], "Итог / 10")
        self.assertEqual(records[1][1:3], ["Анна", "8.50"])

    def test_invalid_score_does_not_change_json(self):
        student = self.app.add_student("Анна")
        criterion = self.app.add_criterion("Практика", "10", "1")
        original = (self.base / "pos.json").read_text(encoding="utf-8")
        with self.assertRaises(ValidationError):
            self.app.set_evaluation(student.id, criterion.id, "11")
        self.assertEqual((self.base / "pos.json").read_text(encoding="utf-8"), original)

    def test_reloading_keeps_evaluations(self):
        student = self.app.add_student("Анна")
        criterion = self.app.add_criterion("Практика", "10", "1")
        self.app.set_evaluation(student.id, criterion.id, "7")
        other = create_container(self.base / "pos.json").resolve("facade")
        self.assertEqual(other.total(student.id).score10, Decimal("7.00"))
        self.assertEqual(len(other.student_evaluations(student.id)), 1)

    def test_injected_strategy_changes_result(self):
        student = self.app.add_student("Анна")
        first = self.app.add_criterion("1", "10", "1")
        self.app.add_criterion("2", "10", "1")
        self.app.set_evaluation(student.id, first.id, "10")
        provisional = create_container(self.base / "pos.json", "provisional").resolve("facade")
        self.assertEqual(self.app.total(student.id).score10, Decimal("5.00"))
        self.assertEqual(provisional.total(student.id).score10, Decimal("10.00"))

    def test_container_returns_singletons(self):
        container = create_container(self.base / "pos.json")
        self.assertIs(container.resolve("facade"), container.resolve("facade"))
        self.assertIs(container.resolve("repository"), container.resolve("repository"))


if __name__ == "__main__":
    unittest.main()
