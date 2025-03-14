import os
import sys
import json
import logging

QUIZ_DATA_FOLDER = os.environ.get("QUIZ_DATA_FOLDER", "quiz_data")

logger = logging.getLogger(__name__)

def load_json_file(filepath):
    """
    Load a JSON file or return None if fails.
    Logs a warning if an error occurs (malformed JSON or missing 'questions' key).
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
            if "questions" not in data:
                logger.warning(f"Missing 'questions' key in JSON: {filepath} - skipping.")
                return None
            return data
    except Exception as ex:
        logger.warning(f"Error loading JSON from '{filepath}' - skipping. Exception: {ex}")
        return None

def discover_quiz_files(folder):
    """Recursively find Test Humanidades 1 parcial AGGIORNATO 10 03 25.json quiz files."""
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith("Test Humanidades 1 parcial AGGIORNATO 10 03 25.json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes(folder=QUIZ_DATA_FOLDER):
    """
    Return (combined_questions, cursos_dict, quiz_files_info).
    - combined_questions: List of all questions from all JSON files
    - cursos_dict: Organized courses/sections data
    - quiz_files_info: Info about each quiz file
    """
    all_files = discover_quiz_files(folder)
    if not all_files:
        print(f"No se encontraron archivos JSON en '{folder}'!")
        sys.exit(1)

    cursos_dict = {}
    combined_questions = []
    quiz_files_info = []

    for filepath in all_files:
        data = load_json_file(filepath)
        if not data:
            # Either malformed or missing "questions" or something else, so skip
            continue

        questions_list = data["questions"]
        file_question_count = len(questions_list)
        quiz_files_info.append({
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "question_count": file_question_count
        })

        # Figure out course/section from folder structure
        rel_path = os.path.relpath(filepath, folder)
        parts = rel_path.split(os.sep)
        curso = parts[0] if len(parts) >= 1 else "(Unknown)"
        if len(parts) > 2:
            section = parts[1]
        elif len(parts) == 2:
            section = None
        else:
            section = None

        if curso not in cursos_dict:
            cursos_dict[curso] = {
                "sections": {},
                "total_files": 0,
                "total_questions": 0
            }
        cursos_dict[curso]["total_files"] += 1
        cursos_dict[curso]["total_questions"] += file_question_count

        if section:
            if section not in cursos_dict[curso]["sections"]:
                cursos_dict[curso]["sections"][section] = {
                    "files": [],
                    "section_questions": 0
                }
            cursos_dict[curso]["sections"][section]["files"].append({
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "question_count": file_question_count
            })
            cursos_dict[curso]["sections"][section]["section_questions"] += file_question_count
        else:
            top_level = "(No subfolder)"
            if top_level not in cursos_dict[curso]["sections"]:
                cursos_dict[curso]["sections"][top_level] = {
                    "files": [],
                    "section_questions": 0
                }
            cursos_dict[curso]["sections"][top_level]["files"].append({
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "question_count": file_question_count
            })
            cursos_dict[curso]["sections"][top_level]["section_questions"] += file_question_count

        # Merge questions
        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)

    return combined_questions, cursos_dict, quiz_files_info
