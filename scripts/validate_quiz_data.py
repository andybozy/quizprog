#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    quiz_data = repo_root / "quiz_data"
    errors: list[str] = []
    warnings: list[str] = []

    if not quiz_data.is_dir():
        errors.append(f"Missing quiz_data directory: {quiz_data}")
        return report(errors, warnings)

    quiz_files = sorted(
        path for path in quiz_data.rglob("*.json")
        if path.name not in {"exam_dates.json", "display_overrides.json", ".quiz_index.json"}
        and not path.name.startswith(".")
    )

    if not quiz_files:
        errors.append("No quiz JSON files found under quiz_data/")

    course_dirs = sorted(
        path for path in quiz_data.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )

    for course_dir in course_dirs:
        has_quiz = any(
            path.suffix == ".json" and path.name not in {".quiz_index.json"} and not path.name.startswith(".")
            for path in course_dir.rglob("*.json")
        )
        if not has_quiz:
            warnings.append(f"Course directory is empty: {course_dir.relative_to(repo_root)}")

    exam_dates_path = quiz_data / "exam_dates.json"
    if not exam_dates_path.exists():
        errors.append("Missing quiz_data/exam_dates.json")
        exam_dates = {}
    else:
        exam_dates = load_json(exam_dates_path, errors)
        if not isinstance(exam_dates, dict):
            errors.append("exam_dates.json must be a JSON object")
            exam_dates = {}

    overrides_path = quiz_data / "display_overrides.json"
    if not overrides_path.exists():
        warnings.append("Missing quiz_data/display_overrides.json")
        overrides = {}
    else:
        override_data = load_json(overrides_path, errors)
        overrides = override_data.get("files", {}) if isinstance(override_data, dict) else {}
        if not isinstance(overrides, dict):
            errors.append("display_overrides.json -> files must be a JSON object")
            overrides = {}

    course_names = {path.parent.relative_to(quiz_data).parts[0] for path in quiz_files}
    for course_name in sorted(course_names - set(exam_dates)):
        warnings.append(f"Missing exam date for course: {course_name}")

    for relative_path in sorted(overrides):
        if not (quiz_data / relative_path).exists():
            errors.append(f"display_overrides.json points to missing file: {relative_path}")

    for quiz_file in quiz_files:
        data = load_json(quiz_file, errors)
        if not isinstance(data, dict):
            errors.append(f"{quiz_file.relative_to(repo_root)} must contain a JSON object")
            continue

        questions = data.get("questions")
        if not isinstance(questions, list) or not questions:
            errors.append(f"{quiz_file.relative_to(repo_root)} has no questions array")
            continue

        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                warnings.append(f"{quiz_file.relative_to(repo_root)} question #{index} is not an object")
                continue

            prompt = str(question.get("question", "")).strip()
            answers = question.get("answers", [])
            if not prompt:
                warnings.append(f"{quiz_file.relative_to(repo_root)} question #{index} has an empty prompt")
            if not isinstance(answers, list) or len(answers) < 2:
                warnings.append(f"{quiz_file.relative_to(repo_root)} question #{index} has fewer than 2 answers")
                continue

            correct_count = 0
            for answer in answers:
                if not isinstance(answer, dict) or not str(answer.get("text", "")).strip():
                    warnings.append(f"{quiz_file.relative_to(repo_root)} question #{index} has an invalid answer")
                    continue
                if bool(answer.get("correct")):
                    correct_count += 1

            if correct_count == 0:
                warnings.append(f"{quiz_file.relative_to(repo_root)} question #{index} has no correct answer")

    return report(errors, warnings)


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to parse {path}: {exc}")
        return {}


def report(errors: list[str], warnings: list[str]) -> int:
    if not errors:
        print("quiz_data validation passed")
        if warnings:
            print("warnings:")
            for warning in warnings:
                print(f"- {warning}")
        return 0

    print("quiz_data validation failed:")
    for error in errors:
        print(f"- {error}")
    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
