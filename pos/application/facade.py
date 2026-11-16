"""Сценарии приложения через один вход для консольного интерфейса."""

from pathlib import Path

from pos.domain.model import AssessmentBook, Criterion, Evaluation, Student
from pos.domain.repositories import AssessmentRepository
from pos.domain.services import GradeSummary, WeightedTotalCalculator

from .ports import ReportWriter


class PosFacade:
    """GoF Facade: UI не координирует домен, репозиторий и экспорт самостоятельно."""

    def __init__(
        self,
        repository: AssessmentRepository,
        calculator: WeightedTotalCalculator,
        report_writer: ReportWriter,
    ) -> None:
        self._repository = repository
        self._calculator = calculator
        self._report_writer = report_writer

    def students(self) -> tuple[Student, ...]:
        return self._repository.load().students()

    def add_student(self, name: str) -> Student:
        book = self._repository.load()
        student = book.add_student(name)
        self._repository.save(book)
        return student

    def remove_student(self, student_id: str) -> None:
        book = self._repository.load()
        book.remove_student(student_id)
        self._repository.save(book)

    def criteria(self) -> tuple[Criterion, ...]:
        return self._repository.load().criteria()

    def add_criterion(self, name: str, maximum: str, weight: str) -> Criterion:
        book = self._repository.load()
        criterion = book.add_criterion(name, maximum, weight)
        self._repository.save(book)
        return criterion

    def remove_criterion(self, criterion_id: str) -> None:
        book = self._repository.load()
        book.remove_criterion(criterion_id)
        self._repository.save(book)

    def set_evaluation(
        self, student_id: str, criterion_id: str, score: str, comment: str = ""
    ) -> Evaluation:
        book = self._repository.load()
        evaluation = book.set_evaluation(student_id, criterion_id, score, comment)
        self._repository.save(book)
        return evaluation

    def cancel_evaluation(self, student_id: str, criterion_id: str) -> None:
        book = self._repository.load()
        book.cancel_evaluation(student_id, criterion_id)
        self._repository.save(book)

    def student_evaluations(self, student_id: str) -> tuple[tuple[Criterion, Evaluation], ...]:
        return self._repository.load().student_evaluations(student_id)

    def total(self, student_id: str) -> GradeSummary:
        book = self._repository.load()
        return self._calculator.calculate(book, student_id)

    def export_report(self, path: Path) -> int:
        book = self._repository.load()
        summaries = tuple(self._calculator.calculate(book, item.id) for item in book.students())
        self._report_writer.write(path, summaries)
        return len(summaries)
