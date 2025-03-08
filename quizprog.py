import os
import json
import random
import sys
import traceback

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.2.0"

def clear():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    input("\nPresiona Enter para continuar...")

def print_local_summary(session_correct, session_wrong, session_unanswered):
    """Muestra un resumen para esta sesión (no global)."""
    total = session_correct + session_wrong + session_unanswered
    print("\n=== Resumen de esta sesión ===")
    print(f"Correctas: {session_correct}")
    print(f"Incorrectas: {session_wrong}")
    print(f"No respondidas (o saltadas): {session_unanswered}")
    print(f"Total en esta sesión: {total}\n")
    press_any_key()

def preguntar(qid, question_data, perf_data, session_counts):
    """
    Muestra UNA pregunta.
    - session_counts = {"correct": ..., "wrong": ..., "unanswered": ...}
    Retorna True si correcto, False si incorrecto, None si usuario intenta salir (presiona 0).
    """
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear()

    question_text = question_data["question"]
    answers_original = question_data["answers"]
    answers_shuffled = answers_original[:]
    random.shuffle(answers_shuffled)

    explanation = question_data.get("explanation", "")
    wrongmsg = question_data.get("wrongmsg", "")

    source_path = question_data.get("_quiz_source", "")
    archivo_origen = os.path.basename(source_path) if source_path else ""
    if archivo_origen:
        print(f"(Pregunta de: {archivo_origen})\n")

    correct_indices = [
        i for i, ans in enumerate(answers_shuffled)
        if ans.get("correct", False)
    ]
    if not correct_indices:
        print(f"[!] Pregunta {qid} sin respuestas correctas; se omite...\n")
        # Marcamos como no-unanswered:
        perf_data[str(qid)]["unanswered"] = False
        # Contamos como "correcta" a efectos de no romper la sesión (opcional).
        session_counts["correct"] += 1
        return True

    multi_correct = (len(correct_indices) > 1)

    print(f"Pregunta {qid}:\n{question_text}\n")
    for i, ans in enumerate(answers_shuffled):
        print(f"[{i+1}] {ans['text']}")
    print("\n[0] Salir de la sesión\n")

    if multi_correct:
        print("Puede haber varias respuestas correctas (ej. '1,3').")

    opcion = input("Tu respuesta: ").strip()
    if opcion == "0":
        # En lugar de salir de inmediato, confirmamos:
        clear()
        print("¿Seguro que deseas salir de esta sesión y volver al sub-menú? (s/n)")
        confirm = input("> ").lower()
        if confirm == "s":
            return None  # Indica al bucle principal que el usuario abandona
        else:
            # “No”, entonces seguimos en la misma pregunta => no penalizamos,
            # pero consideramos no respondida:
            session_counts["unanswered"] += 1
            return False  # or True, but we typically treat as “wrong” or “skipped”
            # Actually you could “redo” the question by returning a special code
            # but let's keep it simple.

    # Procesar la respuesta del usuario
    try:
        seleccion = [int(x) - 1 for x in opcion.split(",")]
    except ValueError:
        seleccion = [-1]

    # Revisar si es correcto
    if not multi_correct:
        if len(seleccion) == 1 and seleccion[0] in correct_indices:
            # Correcto
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            clear()
            print("¡CORRECTO!\n")
            session_counts["correct"] += 1
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return True
        else:
            # Incorrecto
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("¡INCORRECTO!\n")
            session_counts["wrong"] += 1
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False
    else:
        # Multi-correct
        correct_set = set(correct_indices)
        user_set = set(seleccion)
        if user_set == correct_set:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            clear()
            print("¡CORRECTO!\n")
            session_counts["correct"] += 1
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return True
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("¡INCORRECTO!\n")
            session_counts["wrong"] += 1
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False

def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    - If user hits 0 and confirms "salir", we do NOT go to main menu.
      Instead we exit 'play_quiz()' => caller can remain in 'comando_elegir_archivo()'.
    - At the end, we show a local summary of correct/wrong/unanswered for THIS run.
    """
    # 1) Armar subset
    all_pairs = [(i, q) for i, q in enumerate(full_questions)]
    if file_filter is not None:
        all_pairs = [(i, q) for (i, q) in all_pairs if q.get("_quiz_source") == file_filter]

    if filter_mode == "wrong":
        subset = [(i, q) for (i, q) in all_pairs
                  if str(i) in perf_data and perf_data[str(i)]["wrong"]]
    elif filter_mode == "unanswered":
        subset = [(i, q) for (i, q) in all_pairs
                  if str(i) not in perf_data or perf_data[str(i)]["unanswered"]]
    else:
        subset = all_pairs

    if not subset:
        print("\n[No hay preguntas para este filtro. Volviendo...]\n")
        press_any_key()
        return

    # random.shuffle(subset) # si deseas barajar el orden de las preguntas

    # 2) Contadores LOCALES para esta sesión
    session_counts = {
        "correct": 0,
        "wrong": 0,
        "unanswered": 0
    }

    # 3) Bucle principal de preguntas
    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        resultado = preguntar(qid, qdata, perf_data, session_counts)
        # resultado -> True, False, or None
        if resultado is None:
            # Usuario presionó 0 y confirmó "salir" => terminamos
            break

        # Guardar performance
        save_performance_data(perf_data)

        idx += 1

    # Al terminar (porque ya no hay más preguntas o usuario salió),
    # imprimimos un pequeño resumen de la CORRIDA ACTUAL
    clear()
    print_local_summary(session_counts["correct"],
                        session_counts["wrong"],
                        session_counts["unanswered"])

    # Devolvemos sin ir al main menu => volverá a la función que llamó play_quiz
