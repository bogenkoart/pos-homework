"""Консольное приложение ПОС."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from pos.adapters.json_repository import StorageError
from pos.application.facade import PosFacade
from pos.bootstrap import create_container
from pos.domain.model import DomainError


MENU = """
\nПОС — преподавательская оценка студентов
 1. Список студентов       2. Добавить студента       3. Удалить студента
 4. Список критериев       5. Добавить критерий       6. Удалить критерий
 7. Выставить/исправить    8. Оценки студента        9. Отменить оценку
10. Итог студента         11. Экспорт CSV            0. Выход
"""


def show_students(app: PosFacade) -> None:
    students = app.students()
    if not students:
        print("Студентов пока нет.")
    for student in students:
        print(f"  {student.id}  {student.name}")


def show_criteria(app: PosFacade) -> None:
    criteria = app.criteria()
    if not criteria:
        print("Критериев пока нет.")
    for criterion in criteria:
        print(
            f"  {criterion.id}  {criterion.name}: "
            f"макс. {criterion.max_score}, вес {criterion.weight}"
        )


def check_export_path(output: Path, data_file: Path) -> None:
    if output.resolve() == data_file.resolve():
        raise ValueError("Для отчёта укажите путь, отличный от файла данных.")


def execute(app: PosFacade, choice: str, data_file: Path) -> bool:
    if choice == "0":
        return False
    if choice == "1":
        show_students(app)
    elif choice == "2":
        student = app.add_student(input("Имя студента: "))
        print(f"Добавлен: {student.name} ({student.id})")
    elif choice == "3":
        app.remove_student(input("ID студента: ").strip())
        print("Студент и его оценки удалены.")
    elif choice == "4":
        show_criteria(app)
    elif choice == "5":
        criterion = app.add_criterion(
            input("Название критерия: "),
            input("Максимальный балл: ").strip(),
            input("Вес (положительное число): ").strip(),
        )
        print(f"Добавлен критерий: {criterion.name} ({criterion.id})")
    elif choice == "6":
        app.remove_criterion(input("ID критерия: ").strip())
        print("Критерий удалён.")
    elif choice == "7":
        show_students(app)
        student_id = input("ID студента: ").strip()
        show_criteria(app)
        criterion_id = input("ID критерия: ").strip()
        score = input("Балл: ").strip()
        comment = input("Комментарий (можно оставить пустым): ")
        app.set_evaluation(student_id, criterion_id, score, comment)
        print("Оценка сохранена (повторный ввод исправляет её).")
    elif choice == "8":
        student_id = input("ID студента: ").strip()
        evaluations = app.student_evaluations(student_id)
        if not evaluations:
            print("Оценок пока нет.")
        for criterion, grade in evaluations:
            extra = f" — {grade.comment}" if grade.comment else ""
            print(f"  {criterion.name}: {grade.score.value}/{criterion.max_score}{extra}")
    elif choice == "9":
        student_id = input("ID студента: ").strip()
        criterion_id = input("ID критерия: ").strip()
        app.cancel_evaluation(student_id, criterion_id)
        print("Оценка отменена.")
    elif choice == "10":
        summary = app.total(input("ID студента: ").strip())
        print(
            f"{summary.student.name}: {summary.score10}/10 "
            f"({summary.assessed_count}/{summary.criteria_count} критериев, {summary.policy})"
        )
    elif choice == "11":
        path = Path(input("Путь к CSV [report.csv]: ").strip() or "report.csv")
        check_export_path(path, data_file)
        count = app.export_report(path)
        print(f"Экспортировано студентов: {count}. Файл: {path}")
    else:
        print("Нет такого пункта.")
    return True


def run_demo(output: Path, data_file: Path, policy: str) -> None:
    check_export_path(output, data_file)
    container = create_container(data_file, policy, memory=True)
    app = cast(PosFacade, container.resolve("facade"))
    anna = app.add_student("Анна Иванова")
    boris = app.add_student("Борис Петров")
    practice = app.add_criterion("Практические работы", "20", "0.6")
    presentation = app.add_criterion("Защита", "10", "0.4")
    app.set_evaluation(anna.id, practice.id, "18", "Хорошая работа")
    app.set_evaluation(anna.id, presentation.id, "8")
    app.set_evaluation(boris.id, practice.id, "12")
    print("Демонстрационные данные:")
    show_students(app)
    show_criteria(app)
    for student in app.students():
        result = app.total(student.id)
        print(
            f"  {student.name}: {result.score10}/10, "
            f"оценено {result.assessed_count}/{result.criteria_count}"
        )
    app.export_report(output)
    print(f"Отчёт экспортирован в {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ПОС: консольный модуль оценивания студентов")
    parser.add_argument("--data", type=Path, default=Path("data/pos.json"), help="JSON-хранилище")
    parser.add_argument(
        "--policy", choices=("full", "provisional"), default="full",
        help="full: невыставленные оценки = 0; provisional: только выставленные",
    )
    parser.add_argument(
        "--demo", action="store_true", help="демонстрация без изменения основной базы"
    )
    parser.add_argument(
        "--export", type=Path, default=Path("demo_result.csv"), help="CSV для --demo"
    )
    args = parser.parse_args()
    try:
        if args.demo:
            run_demo(args.export, args.data, args.policy)
            return 0
        app = cast(PosFacade, create_container(args.data, args.policy).resolve("facade"))
        while True:
            print(MENU)
            try:
                if not execute(app, input("Ваш выбор: ").strip(), args.data):
                    break
            except (DomainError, StorageError, ValueError, OSError) as exc:
                print(f"Ошибка: {exc}")
            except (EOFError, KeyboardInterrupt):
                print("\nЗавершение работы.")
                break
        return 0
    except (StorageError, DomainError, ValueError, OSError) as exc:
        print(f"Ошибка: {exc}")
        return 1
