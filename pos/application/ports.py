"""Порт экспорта отчёта."""

from pathlib import Path
from typing import Protocol

from pos.domain.services import GradeSummary


class ReportWriter(Protocol):
    def write(self, path: Path, summaries: tuple[GradeSummary, ...]) -> None: ...
