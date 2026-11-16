"""Предметная модель преподавательской оценки студентов."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4


class DomainError(Exception):
    """Нарушение бизнес-правил."""


class ValidationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


def to_decimal(value: Decimal | str | int | float) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError("Ожидается число.") from exc
    if not result.is_finite():
        raise ValidationError("Число должно быть конечным.")
    return result


def required_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Поле «{field}» не может быть пустым.")
    return value.strip()


@dataclass(frozen=True, slots=True)
class Score:
    """Value Object: неотрицательное числовое значение балла."""

    value: Decimal

    def __post_init__(self) -> None:
        value = to_decimal(self.value)
        if value < 0:
            raise ValidationError("Балл не может быть отрицательным.")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class Student:
    id: str
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", required_text(self.id, "ID студента"))
        object.__setattr__(self, "name", required_text(self.name, "Имя студента"))


@dataclass(frozen=True, slots=True)
class Criterion:
    id: str
    name: str
    max_score: Decimal
    weight: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", required_text(self.id, "ID критерия"))
        object.__setattr__(self, "name", required_text(self.name, "Название критерия"))
        maximum = to_decimal(self.max_score)
        weight = to_decimal(self.weight)
        if maximum <= 0:
            raise ValidationError("Максимальный балл должен быть больше нуля.")
        if weight <= 0:
            raise ValidationError("Вес критерия должен быть больше нуля.")
        object.__setattr__(self, "max_score", maximum)
        object.__setattr__(self, "weight", weight)


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Entity, идентифицируемая парой (student_id, criterion_id)."""

    student_id: str
    criterion_id: str
    score: Score
    comment: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        required_text(self.student_id, "ID студента")
        required_text(self.criterion_id, "ID критерия")
        if not isinstance(self.score, Score):
            raise ValidationError("Оценка должна содержать Score.")
        if not isinstance(self.comment, str):
            raise ValidationError("Комментарий должен быть строкой.")
        if not isinstance(self.recorded_at, datetime) or self.recorded_at.tzinfo is None:
            raise ValidationError("Дата оценки должна содержать часовой пояс.")


class EvaluationFactory(ABC):
    """GoF Factory Method: общие проверки и заменяемое создание оценки."""

    def create(
        self,
        student_id: str,
        criterion: Criterion,
        score: Decimal | str | int | float,
        comment: str = "",
    ) -> Evaluation:
        result = Score(to_decimal(score))
        if result.value > criterion.max_score:
            raise ValidationError(
                f"По критерию «{criterion.name}» разрешено не больше {criterion.max_score} баллов."
            )
        return self._make_evaluation(student_id, criterion.id, result, comment)

    @abstractmethod
    def _make_evaluation(
        self, student_id: str, criterion_id: str, score: Score, comment: str
    ) -> Evaluation:
        """Фабричный метод: подкласс выбирает способ создания объекта."""


class NewEvaluationFactory(EvaluationFactory):
    def _make_evaluation(
        self, student_id: str, criterion_id: str, score: Score, comment: str
    ) -> Evaluation:
        return Evaluation(student_id, criterion_id, score, comment, datetime.now(timezone.utc))


class RestoredEvaluationFactory(EvaluationFactory):
    def __init__(self, recorded_at: datetime) -> None:
        self._recorded_at = recorded_at

    def _make_evaluation(
        self, student_id: str, criterion_id: str, score: Score, comment: str
    ) -> Evaluation:
        return Evaluation(student_id, criterion_id, score, comment, self._recorded_at)


class AssessmentBook:
    """Агрегат: студенты, рубрикатор и выставленные оценки одного курса."""

    def __init__(self) -> None:
        self._students: dict[str, Student] = {}
        self._criteria: dict[str, Criterion] = {}
        self._evaluations: dict[tuple[str, str], Evaluation] = {}

    def students(self) -> tuple[Student, ...]:
        return tuple(sorted(self._students.values(), key=lambda s: (s.name.casefold(), s.id)))

    def criteria(self) -> tuple[Criterion, ...]:
        return tuple(sorted(self._criteria.values(), key=lambda c: (c.name.casefold(), c.id)))

    def evaluations(self) -> tuple[Evaluation, ...]:
        return tuple(
            sorted(self._evaluations.values(), key=lambda e: (e.student_id, e.criterion_id))
        )

    def student(self, student_id: str) -> Student:
        try:
            return self._students[student_id]
        except KeyError as exc:
            raise NotFoundError(f"Студент с ID {student_id} не найден.") from exc

    def criterion(self, criterion_id: str) -> Criterion:
        try:
            return self._criteria[criterion_id]
        except KeyError as exc:
            raise NotFoundError(f"Критерий с ID {criterion_id} не найден.") from exc

    def add_student(self, name: str, student_id: str | None = None) -> Student:
        student = Student(student_id if student_id is not None else uuid4().hex[:8], name)
        if student.id in self._students:
            raise ConflictError(f"Студент с ID {student.id} уже существует.")
        self._students[student.id] = student
        return student

    def remove_student(self, student_id: str) -> None:
        self.student(student_id)
        del self._students[student_id]
        self._evaluations = {
            key: value for key, value in self._evaluations.items() if key[0] != student_id
        }

    def add_criterion(
        self,
        name: str,
        max_score: Decimal | str | int | float,
        weight: Decimal | str | int | float,
        criterion_id: str | None = None,
    ) -> Criterion:
        criterion = Criterion(
            criterion_id if criterion_id is not None else uuid4().hex[:8],
            name,
            to_decimal(max_score),
            to_decimal(weight),
        )
        if criterion.id in self._criteria:
            raise ConflictError(f"Критерий с ID {criterion.id} уже существует.")
        self._criteria[criterion.id] = criterion
        return criterion

    def remove_criterion(self, criterion_id: str) -> None:
        self.criterion(criterion_id)
        if any(key[1] == criterion_id for key in self._evaluations):
            raise ConflictError("Сначала отмените оценки по этому критерию.")
        del self._criteria[criterion_id]

    def set_evaluation(
        self,
        student_id: str,
        criterion_id: str,
        score: Decimal | str | int | float,
        comment: str = "",
        recorded_at: datetime | None = None,
    ) -> Evaluation:
        self.student(student_id)
        criterion = self.criterion(criterion_id)
        factory = (
            NewEvaluationFactory()
            if recorded_at is None
            else RestoredEvaluationFactory(recorded_at)
        )
        evaluation = factory.create(student_id, criterion, score, comment)
        self._evaluations[(student_id, criterion_id)] = evaluation
        return evaluation

    def cancel_evaluation(self, student_id: str, criterion_id: str) -> None:
        self.student(student_id)
        self.criterion(criterion_id)
        try:
            del self._evaluations[(student_id, criterion_id)]
        except KeyError as exc:
            raise NotFoundError("Такая оценка не выставлена.") from exc

    def student_evaluations(self, student_id: str) -> tuple[tuple[Criterion, Evaluation], ...]:
        self.student(student_id)
        return tuple(
            (criterion, self._evaluations[(student_id, criterion.id)])
            for criterion in self.criteria()
            if (student_id, criterion.id) in self._evaluations
        )
