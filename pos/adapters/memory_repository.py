"""In-memory адаптер для тестов и демонстрации."""

from pos.domain.model import AssessmentBook


class InMemoryAssessmentRepository:
    def __init__(self) -> None:
        self._book = AssessmentBook()

    def load(self) -> AssessmentBook:
        return self._book

    def save(self, book: AssessmentBook) -> None:
        self._book = book
