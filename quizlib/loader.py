# quizprog/quizlib/loader.py

import os
import sys
import json

QUIZ_DATA_FOLDER = os.environ.get("QUIZ_DATA_FOLDER", "quiz_data")

def load_json_file(filepath):
    """Carga un archivo JSON, o None si falla."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Error al cargar '{filepath}': {ex}")
        return None

def discover_quiz_files(folder):
    """Recursively find .json quiz files in the folder."""
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes(folder=QUIZ_DATA_FOLDER):
    """
    1) Carga todos los .json en `folder`.
    2) Returns a tuple of:
       ( combined_questions,
         cursos_dict,
         quiz_files_info )

       - combined_questions: list of all questions
       - cursos_dict: info about each curso, sections, files, totals
       - quiz_files_info: info about each loaded .json file
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
        if not data or "questions" not in data:
            continue

        questions_list = data["questions"]
        file_question_count = len(questions_list)
        quiz_files_info.append({
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "question_count": file_question_count
        })

        rel_path = os.path.relpath(filepath, folder)
        parts = rel_path.split(os.sep)
        curso = parts[0]
        if len(parts) > 2:
            # folder/section/file.json
            section = parts[1]
        elif len(parts) == 2:
            # folder/file.json
            section = None
        else:
            # file.json at root
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
            top_level_section = "(No subfolder)"
            if top_level_section not in cursos_dict[curso]["sections"]:
                cursos_dict[curso]["sections"][top_level_section] = {
                    "files": [],
                    "section_questions": 0
                }
            cursos_dict[curso]["sections"][top_level_section]["files"].append({
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "question_count": file_question_count
            })
            cursos_dict[curso]["sections"][top_level_section]["section_questions"] += file_question_count

        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)

    return combined_questions, cursos_dict, quiz_files_info
