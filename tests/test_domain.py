import unittest
from decimal import Decimal

from pos.domain.model import AssessmentBook, ConflictError, NotFoundError, ValidationError
from pos.domain.services import AssessedOnly, MissingAsZero, WeightedTotalCalculator


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.book = AssessmentBook()
        self.student = self.book.add_student("Анна")
        self.practice = self.book.add_criterion("Практика", "20", "0.6")
        self.defense = self.book.add_criterion("Защита", "10", "0.4")

    def test_negative_score_rejected(self):
        with self.assertRaises(ValidationError):
            self.book.set_evaluation(self.student.id, self.practice.id, "-1")

    def test_above_maximum_rejected(self):
        with self.assertRaises(ValidationError):
            self.book.set_evaluation(self.student.id, self.practice.id, "20.1")

    def test_exact_maximum_accepted(self):
        evaluation = self.book.set_evaluation(self.student.id, self.practice.id, "20")
        self.assertEqual(evaluation.score.value, Decimal("20"))

    def test_unknown_criterion_rejected(self):
        with self.assertRaises(NotFoundError):
            self.book.set_evaluation(self.student.id, "unknown", "3")

    def test_unknown_student_rejected(self):
        with self.assertRaises(NotFoundError):
            self.book.set_evaluation("unknown", self.practice.id, "3")

    def test_invalid_criterion_rejected(self):
        for maximum, weight in (("0", "1"), ("10", "0"), ("-2", "1"), ("5", "-1")):
            with self.subTest(maximum=maximum, weight=weight):
                with self.assertRaises(ValidationError):
                    self.book.add_criterion("Некорректный", maximum, weight)

    def test_nan_and_infinity_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.book.set_evaluation(self.student.id, self.practice.id, value)

    def test_empty_student_name_rejected(self):
        with self.assertRaises(ValidationError):
            self.book.add_student("   ")

    def test_grade_correction_replaces_previous(self):
        self.book.set_evaluation(self.student.id, self.practice.id, "10")
        self.book.set_evaluation(self.student.id, self.practice.id, "17")
        self.assertEqual(len(self.book.evaluations()), 1)
        self.assertEqual(self.book.evaluations()[0].score.value, Decimal("17"))

    def test_cancel_grade(self):
        self.book.set_evaluation(self.student.id, self.practice.id, "5")
        self.book.cancel_evaluation(self.student.id, self.practice.id)
        self.assertEqual(self.book.evaluations(), ())

    def test_removing_criterion_with_grades_is_blocked(self):
        self.book.set_evaluation(self.student.id, self.practice.id, "5")
        with self.assertRaises(ConflictError):
            self.book.remove_criterion(self.practice.id)

    def test_removing_student_cascades_grades(self):
        self.book.set_evaluation(self.student.id, self.practice.id, "5")
        self.book.remove_student(self.student.id)
        self.assertEqual(self.book.evaluations(), ())

    def test_full_weighted_total(self):
        self.book.set_evaluation(self.student.id, self.practice.id, "18")
        self.book.set_evaluation(self.student.id, self.defense.id, "8")
        summary = WeightedTotalCalculator(MissingAsZero()).calculate(self.book, self.student.id)
        self.assertEqual(summary.score10, Decimal("8.60"))
        self.assertEqual(summary.assessed_count, 2)

    def test_missing_grades_as_zero(self):
        self.book.set_evaluation(self.student.id, self.practice.id, "12")
        summary = WeightedTotalCalculator(MissingAsZero()).calculate(self.book, self.student.id)
        self.assertEqual(summary.score10, Decimal("3.60"))

    def test_provisional_ignores_missing_criteria(self):
        self.book.set_evaluation(self.student.id, self.practice.id, "12")
        summary = WeightedTotalCalculator(AssessedOnly()).calculate(self.book, self.student.id)
        self.assertEqual(summary.score10, Decimal("6.00"))

    def test_no_grades_yields_zero(self):
        for policy in (MissingAsZero(), AssessedOnly()):
            with self.subTest(policy=policy.name):
                summary = WeightedTotalCalculator(policy).calculate(self.book, self.student.id)
                self.assertEqual(summary.score10, Decimal("0.00"))

    def test_no_criteria_yields_zero(self):
        empty = AssessmentBook()
        person = empty.add_student("Борис")
        self.assertEqual(
            WeightedTotalCalculator(MissingAsZero()).calculate(empty, person.id).score10,
            Decimal("0.00"),
        )


if __name__ == "__main__":
    unittest.main()
