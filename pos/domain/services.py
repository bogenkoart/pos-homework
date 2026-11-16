"""Расчёт итогов; правило учёта пропусков заменяется стратегией."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from .model import AssessmentBook, Criterion, Student


class MissingGradePolicy(Protocol):
    name: str

    def denominator(
        self, criteria: tuple[Criterion, ...], assessed_ids: frozenset[str]
    ) -> Decimal: ...


class MissingAsZero:
    """Неоценённый критерий учитывается как ноль (финальный результат)."""

    name = "Полный"

    def denominator(
        self, criteria: tuple[Criterion, ...], assessed_ids: frozenset[str]
    ) -> Decimal:
        return sum((item.weight for item in criteria), Decimal("0"))


class AssessedOnly:
    """Для промежуточного просмотра учитываются только оценённые критерии."""

    name = "Промежуточный"

    def denominator(
        self, criteria: tuple[Criterion, ...], assessed_ids: frozenset[str]
    ) -> Decimal:
        return sum((item.weight for item in criteria if item.id in assessed_ids), Decimal("0"))


@dataclass(frozen=True, slots=True)
class GradeSummary:
    student: Student
    score10: Decimal
    assessed_count: int
    criteria_count: int
    policy: str


class WeightedTotalCalculator:
    """Domain Service, делегирующий учёт пропусков GoF Strategy."""

    def __init__(self, policy: MissingGradePolicy) -> None:
        self._policy = policy

    def calculate(self, book: AssessmentBook, student_id: str) -> GradeSummary:
        student = book.student(student_id)
        criteria = book.criteria()
        grades = {criterion.id: grade for criterion, grade in book.student_evaluations(student_id)}
        numerator = sum(
            (
                criterion.weight * grades[criterion.id].score.value / criterion.max_score
                for criterion in criteria
                if criterion.id in grades
            ),
            Decimal("0"),
        )
        denominator = self._policy.denominator(criteria, frozenset(grades))
        score10 = (
            (numerator / denominator * Decimal("10")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if denominator > 0
            else Decimal("0.00")
        )
        return GradeSummary(student, score10, len(grades), len(criteria), self._policy.name)
