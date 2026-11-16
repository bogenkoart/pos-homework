"""Порт хранения: домен ничего не знает о формате данных."""

from typing import Protocol

from .model import AssessmentBook


class AssessmentRepository(Protocol):
    def load(self) -> AssessmentBook: ...

    def save(self, book: AssessmentBook) -> None: ...
