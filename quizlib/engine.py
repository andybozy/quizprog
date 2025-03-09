# quizprog/quizlib/engine.py

import os
import random
import re

from .performance import save_performance_data
from .utils import clear_screen, press_any_key

def sanitize_question_text(text):
    """
    Quita líneas que comienzan con 'a)', 'b)', 'c)', 'd)', '(a)', '(b)', etc.
    para no duplicar las respuestas en el enunciado.
    """
    lines = text.splitlines()
    new_lines = []
    pattern = re.compile(r"^\s*(?:\(?[abcd]\)|[abcd]\))(\s|$)", re.IGNORECASE)
    for line in lines:
        if pattern.match(line.strip()):
            continue
        new_lines.append(line)
    return "\n".join(new_lines).strip()

def preguntar(qid, question_data, perf_data, session_counts):
    """
    Muestra UNA pregunta. Devuelve:
      True => correcto
      False => incorrecto
      None => usuario sale
    """
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear_screen()

    original_text = question_data["question"]
    question_text = sanitize_question_text(original_text)

    answers_original = question_data["answers"]
    answers_shuffled = answers_original[:]
    random.shuffle(answers_shuffled)

    explanation = question_data.get("explanation", "")
    wrongmsg = question_data.get("wrongmsg", "")

    source_path = question_data.get("_quiz_source", "")
    archivo_origen = os.path.basename(source_path) if source_path else ""
    if archivo_origen:
        print(f"(Pregunta de: {archivo_origen})\n")

    correct_indices = [i for i, ans in enumerate(answers_shuffled) if ans.get("correct", False)]
    if not correct_indices:
        print(f"[!] Pregunta {qid} sin respuestas correctas; se omite...\n")
        perf_data[str(qid)]["unanswered"] = False
        session_counts["correct"] += 1
        return True

    multi_correct = (len(correct_indices) > 1)

    print(f"Pregunta {qid}:\n{question_text}\n")

    LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i, ans in enumerate(answers_shuffled):
        label = LETTERS[i]
        print(f"[{label}] {ans['text']}")

    print("\n[0] Salir de la sesión\n")
    if multi_correct:
        print("Puede haber varias respuestas correctas. Ejemplo: 'A,C'")

    opcion = input("Tu respuesta: ").strip().upper()
    if opcion == "0":
        clear_screen()
        print("¿Seguro que deseas salir de esta sesión y volver al sub-menú? (s/n)")
        confirm = input("> ").lower()
        if confirm == "s":
            return None
        else:
            session_counts["unanswered"] += 1
            return False

    user_positions = []
    try:
        parts = opcion.split(",")
        for p in parts:
            p = p.strip()
            if p:
                idx = ord(p) - ord('A')
                user_positions.append(idx)
    except ValueError:
        user_positions = [-1]

    if not multi_correct:
        # single-correct
        if len(user_positions) == 1 and user_positions[0] in correct_indices:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            session_counts["correct"] += 1

            clear_screen()
            print("¡CORRECTO!\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return True
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            session_counts["wrong"] += 1

            clear_screen()
            print("¡INCORRECTO!\n")
            if wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False
    else:
        # multi-correct
        correct_set = set(correct_indices)
        user_set = set(user_positions)
        if user_set == correct_set:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            session_counts["correct"] += 1

            clear_screen()
            print("¡CORRECTO!\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return True
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            session_counts["wrong"] += 1

            clear_screen()
            print("¡INCORRECTO!\n")
            if wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False

def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    filter_mode: "all", "unanswered", "wrong"
    file_filter: if not None => only questions w/ _quiz_source=that file
    """
    from .performance import save_performance_data

    all_pairs = [(i, q) for i, q in enumerate(full_questions)]
    if file_filter is not None:
        all_pairs = [(i, q) for (i, q) in all_pairs if q.get("_quiz_source") == file_filter]

    if filter_mode == "wrong":
        subset = [(i, q) for (i, q) in all_pairs if str(i) in perf_data and perf_data[str(i)]["wrong"]]
    elif filter_mode == "unanswered":
        subset = [(i, q) for (i, q) in all_pairs if str(i) not in perf_data or perf_data[str(i)]["unanswered"]]
    else:
        subset = all_pairs

    if not subset:
        print("\n[No hay preguntas para este filtro. Volviendo...]\n")
        press_any_key()
        return

    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}

    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        resultado = preguntar(qid, qdata, perf_data, session_counts)
        if resultado is None:
            break
        save_performance_data(perf_data)
        idx += 1

    clear_screen()
    c = session_counts["correct"]
    w = session_counts["wrong"]
    u = session_counts["unanswered"]
    total = c + w + u

    print("\n=== Resumen de esta sesión ===")
    print(f"Correctas: {c}")
    print(f"Incorrectas: {w}")
    print(f"No respondidas (o saltadas): {u}")
    print(f"Total en esta sesión: {total}\n")
    press_any_key()
