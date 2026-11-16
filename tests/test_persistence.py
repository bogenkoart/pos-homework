import json
import tempfile
import unittest
from pathlib import Path

from pos.adapters.json_repository import JsonAssessmentRepository, StorageError
from pos.domain.model import AssessmentBook


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "db.json"
        self.repo = JsonAssessmentRepository(self.path)

    def test_missing_file_gives_empty_book(self):
        self.assertEqual(self.repo.load().students(), ())

    def test_roundtrip_preserves_score_comment_and_timestamp(self):
        book = AssessmentBook()
        student = book.add_student("Анна")
        criterion = book.add_criterion("Проект", "20", "2")
        book.set_evaluation(student.id, criterion.id, "13.5", "Без замечаний")
        original = book.evaluations()[0]
        self.repo.save(book)
        saved = self.repo.load()
        grade = saved.evaluations()[0]
        self.assertEqual(grade.score.value, original.score.value)
        self.assertEqual(grade.recorded_at, original.recorded_at)
        self.assertEqual(grade.comment, "Без замечаний")

    def test_unknown_criterion_in_file_rejected(self):
        data = {
            "version": 1,
            "students": [{"id": "s1", "name": "Анна"}],
            "criteria": [],
            "evaluations": [
                {
                    "student_id": "s1",
                    "criterion_id": "missing",
                    "score": "1",
                    "comment": "",
                    "recorded_at": "2026-11-16T15:00:00+00:00",
                }
            ],
        }
        self.path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(StorageError):
            self.repo.load()

    def test_malformed_json_rejected(self):
        self.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.repo.load()

    def test_score_out_of_range_in_file_rejected(self):
        book = AssessmentBook()
        student = book.add_student("Анна")
        criterion = book.add_criterion("Проект", "10", "1")
        book.set_evaluation(student.id, criterion.id, "9")
        self.repo.save(book)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["evaluations"][0]["score"] = "99"
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(StorageError):
            self.repo.load()


if __name__ == "__main__":
    unittest.main()
