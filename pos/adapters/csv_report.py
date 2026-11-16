"""CSV-адаптер отчёта."""

import csv
import os
import tempfile
from pathlib import Path

from pos.domain.services import GradeSummary


class CsvReportWriter:
    def write(self, path: Path, summaries: tuple[GradeSummary, ...]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=".pos-report-", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["ID", "Студент", "Итог / 10", "Оценено", "Критериев", "Режим"])
                for item in summaries:
                    writer.writerow(
                        [
                            item.student.id,
                            item.student.name,
                            str(item.score10),
                            item.assessed_count,
                            item.criteria_count,
                            item.policy,
                        ]
                    )
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
