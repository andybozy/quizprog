# quizprog/quizlib/loader.py

import os
import sys
import json

# Use environment variable QUIZ_DATA_FOLDER if provided, else default to "quiz_data"
QUIZ_DATA_FOLDER = os.environ.get("QUIZ_DATA_FOLDER", "quiz_data")

def clear():
    """Optionally, you can relocate 'clear()' or remove it if it belongs to CLI only."""
    try:
        os.system("cls" if os.name == 'nt' else "clear")
    except:
        pass

def load_json_file(filepath):
    """Carga un archivo JSON, o None si falla."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Error al cargar '{filepath}': {ex}")
        return None

def descubrir_quiz_files(folder):
    """Encuentra recursivamente todos los .json en la carpeta dada."""
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes(folder=QUIZ_DATA_FOLDER):
    """
    1) Carga todos los .json en 'folder' (por defecto QUIZ_DATA_FOLDER).
    2) Retorna (combined_questions, cursos_dict, cursos_archivos).
    """
    all_files = descubrir_quiz_files(folder)
    if not all_files:
        print(f"No se encontraron archivos JSON en '{folder}'!")
        sys.exit(1)

    cursos_dict = {}
    cursos_archivos = {}
    combined_questions = []

    for filepath in all_files:
        data = load_json_file(filepath)
        if not data or "questions" not in data:
            continue

        questions_list = data["questions"]
        file_question_count = len(questions_list)

        # Determinar curso por subcarpeta:
        rel_path = os.path.relpath(filepath, folder)
        parts = rel_path.split(os.sep)
        curso = parts[0]  # first segment

        if curso not in cursos_dict:
            cursos_dict[curso] = []
        if curso not in cursos_archivos:
            cursos_archivos[curso] = {}

        filename_only = os.path.basename(filepath)

        cursos_dict[curso].append({
            "filename": filename_only,
            "filepath": filepath,
            "question_count": file_question_count
        })

        cursos_archivos[curso][filepath] = {
            "filename": filename_only,
            "questions": [],
            "question_count": file_question_count
        }

        # Agregar a combined_questions y al dict curso->archivo
        for q in questions_list:
            # IMPORTANT: our library expects key "question" (not "q")
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)
                cursos_archivos[curso][filepath]["questions"].append(q)

    return combined_questions, cursos_dict, cursos_archivos
