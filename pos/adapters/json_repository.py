"""JSON-адаптер репозитория с валидацией при загрузке и атомарным сохранением."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from pos.domain.model import AssessmentBook, DomainError


class StorageError(Exception):
    pass


class JsonAssessmentRepository:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def load(self) -> AssessmentBook:
        book = AssessmentBook()
        if not self._path.exists():
            return book
        try:
            with self._path.open("r", encoding="utf-8") as stream:
                content = json.load(stream)
            if not isinstance(content, dict) or content.get("version") != 1:
                raise StorageError("Неизвестная версия файла данных.")
            for student in content["students"]:
                book.add_student(student["name"], student_id=student["id"])
            for criterion in content["criteria"]:
                book.add_criterion(
                    criterion["name"],
                    criterion["max_score"],
                    criterion["weight"],
                    criterion_id=criterion["id"],
                )
            for evaluation in content["evaluations"]:
                book.set_evaluation(
                    evaluation["student_id"],
                    evaluation["criterion_id"],
                    evaluation["score"],
                    evaluation["comment"],
                    datetime.fromisoformat(evaluation["recorded_at"]),
                )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, DomainError) as exc:
            raise StorageError("Файл данных повреждён или нарушает правила оценивания.") from exc
        return book

    def save(self, book: AssessmentBook) -> None:
        content = {
            "version": 1,
            "students": [{"id": s.id, "name": s.name} for s in book.students()],
            "criteria": [
                {
                    "id": c.id,
                    "name": c.name,
                    "max_score": str(c.max_score),
                    "weight": str(c.weight),
                }
                for c in book.criteria()
            ],
            "evaluations": [
                {
                    "student_id": e.student_id,
                    "criterion_id": e.criterion_id,
                    "score": str(e.score.value),
                    "comment": e.comment,
                    "recorded_at": e.recorded_at.isoformat(),
                }
                for e in book.evaluations()
            ],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=".pos-", suffix=".tmp", dir=self._path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(content, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, self._path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
