"""Composition root: простой DI-контейнер с singleton-провайдерами."""

from pathlib import Path
from typing import Callable

from pos.adapters.csv_report import CsvReportWriter
from pos.adapters.json_repository import JsonAssessmentRepository
from pos.adapters.memory_repository import InMemoryAssessmentRepository
from pos.application.facade import PosFacade
from pos.domain.services import AssessedOnly, MissingAsZero, WeightedTotalCalculator


class Container:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[["Container"], object]] = {}
        self._instances: dict[str, object] = {}
        self._resolving: set[str] = set()

    def register(self, key: str, factory: Callable[["Container"], object]) -> None:
        if key in self._factories:
            raise ValueError(f"Зависимость {key} уже зарегистрирована.")
        self._factories[key] = factory

    def resolve(self, key: str) -> object:
        if key in self._instances:
            return self._instances[key]
        if key not in self._factories:
            raise KeyError(f"Неизвестная зависимость: {key}")
        if key in self._resolving:
            raise ValueError(f"Циклическая зависимость: {key}")
        self._resolving.add(key)
        try:
            instance = self._factories[key](self)
            self._instances[key] = instance
            return instance
        finally:
            self._resolving.remove(key)


def create_container(data_file: Path, policy: str = "full", memory: bool = False) -> Container:
    if policy not in ("full", "provisional"):
        raise ValueError(f"Неизвестный режим: {policy}")
    container = Container()
    container.register(
        "repository",
        lambda c: (
            InMemoryAssessmentRepository()
            if memory
            else JsonAssessmentRepository(data_file)
        ),
    )
    container.register(
        "policy", lambda c: MissingAsZero() if policy == "full" else AssessedOnly()
    )
    container.register("calculator", lambda c: WeightedTotalCalculator(c.resolve("policy")))
    container.register("writer", lambda c: CsvReportWriter())
    container.register(
        "facade",
        lambda c: PosFacade(c.resolve("repository"), c.resolve("calculator"), c.resolve("writer")),
    )
    return container
