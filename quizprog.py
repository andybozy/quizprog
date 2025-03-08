import os
import json
import random
import sys
import traceback

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.0.3"

def clear():
    """Limpia la pantalla."""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    """Pausa hasta que el usuario presione Enter."""
    input("\nPresiona Enter para continuar...")

def load_json_file(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Error al cargar '{filepath}': {ex}")
        return None

def descubrir_quiz_files(folder):
    """Obtiene la lista de archivos .json en la carpeta (recursivo)."""
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes():
    """
    Carga todos los .json y los agrupa por “curso” (la primera subcarpeta).
    Además, genera una lista global de preguntas unificadas.
    """
    all_files = descubrir_quiz_files(QUIZ_DATA_FOLDER)
    if not all_files:
        print(f"No se encontraron archivos JSON en '{QUIZ_DATA_FOLDER}'!")
        sys.exit(1)

    cursos_dict = {}
    combined_questions = []

    for filepath in all_files:
        data = load_json_file(filepath)
        if not data or "questions" not in data:
            continue  # ignora archivos sin 'questions'

        questions_list = data["questions"]
        file_question_count = len(questions_list)

        # Curso = primer subcarpeta en la ruta relativa
        rel_path = os.path.relpath(filepath, QUIZ_DATA_FOLDER)
        parts = rel_path.split(os.sep)
        curso = parts[0]

        if curso not in cursos_dict:
            cursos_dict[curso] = []

        filename_only = os.path.basename(filepath)

        cursos_dict[curso].append({
            "filename": filename_only,
            "filepath": filepath,
            "question_count": file_question_count
        })

        # Unir preguntas a la lista global
        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath  # opcional
                combined_questions.append(q)

    return combined_questions, cursos_dict

def print_cursos_summary(cursos_dict):
    """
    Imprime cuántos archivos y preguntas tiene cada curso.
    """
    print("=== RESUMEN DE CURSOS ===\n")
    total_archivos = 0
    total_preguntas = 0

    for curso, files_info in cursos_dict.items():
        count_archivos = len(files_info)
        count_preguntas = sum(fi["question_count"] for fi in files_info)
        total_archivos += count_archivos
        total_preguntas += count_preguntas

        print(f"- Curso: {curso} → {count_archivos} archivos, {count_preguntas} preguntas totales")
        for info in files_info:
            print(f"   • {info['filename']} ({info['question_count']} preguntas)")
        print()

    print(f"** Total: {total_archivos} archivos, {total_preguntas} preguntas en total **\n")
    press_any_key()

def load_performance_data():
    """Carga el archivo local con flags de respuestas (correcto/erróneo/sin contestar)."""
    if not os.path.exists(PERFORMANCE_FILE):
        return {}
    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_performance_data(perf_data):
    """Guarda los datos de desempeño en disco."""
    try:
        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")

def preguntar(qid, question_data, perf_data):
    """
    Muestra una pregunta. Retorna:
      True  -> correcto
      False -> erróneo
      None  -> usuario salió
    Actualiza perf_data.
    """
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear()

    question_text = question_data["question"]
    answers = question_data["answers"]
    explanation = question_data.get("explanation", "")
    wrongmsg = question_data.get("wrongmsg", "")

    correct_indices = [i for i, ans in enumerate(answers) if ans.get("correct")]
    if not correct_indices:
        print(f"[!] Pregunta {qid} sin respuestas correctas, se omite...\n")
        perf_data[str(qid)]["unanswered"] = False
        return True  # la tratamos como “no-problema”

    multi_correct = (len(correct_indices) > 1)

    print(f"Pregunta {qid}:\n{question_text}\n")
    for i, ans in enumerate(answers):
        print(f"[{i+1}] {ans['text']}")
    print("\n[0] Salir de la sesión\n")

    if multi_correct:
        print("Puede haber varias respuestas correctas.\n"
              "Ingresa los números separados por comas (ej. '1,3').\n")

    opcion = input("Tu respuesta: ").strip()
    if opcion == "0":
        perf_data[str(qid)]["unanswered"] = True
        return None

    try:
        seleccion = [int(x) - 1 for x in opcion.split(",")]
    except ValueError:
        seleccion = [-1]

    if not multi_correct:
        # 1 sola respuesta
        if len(seleccion) == 1 and seleccion[0] in correct_indices:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            if explanation:
                clear()
                print("¡CORRECTO!\n")
                print(f"EXPLICACIÓN:\n{explanation}\n")
                press_any_key()
            return True
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("¡INCORRECTO!\n")
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            press_any_key()
            return False
    else:
        # Varias respuestas correctas
        correct_set = set(correct_indices)
        user_set = set(seleccion)
        if user_set == correct_set:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            if explanation:
                clear()
                print("¡CORRECTO!\n")
                print(f"EXPLICACIÓN:\n{explanation}\n")
                press_any_key()
            return True
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("¡INCORRECTO!\n")
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            press_any_key()
            return False

def print_scoreboard(questions, perf_data):
    """
    Muestra la cuenta de correctas, erróneas, sin responder, y total.
    """
    total = len(questions)
    correct = 0
    wrong = 0
    unanswered = 0

    for i in range(total):
        pd = perf_data.get(str(i))
        if not pd:
            unanswered += 1
        else:
            if pd["unanswered"]:
                unanswered += 1
            elif pd["wrong"]:
                wrong += 1
            else:
                correct += 1

    print(f"\n** Estadísticas: Correctas: {correct}, Erróneas: {wrong}, "
          f"Sin responder: {unanswered}, Total: {total} **\n")


def play_quiz(questions, perf_data, filter_mode="all"):
    """
    filter_mode: "all", "unanswered" o "wrong".
    """
    if filter_mode == "wrong":
        subset = [(i, q) for i, q in enumerate(questions)
                  if str(i) in perf_data and perf_data[str(i)]["wrong"]]
    elif filter_mode == "unanswered":
        subset = [(i, q) for i, q in enumerate(questions)
                  if str(i) not in perf_data or perf_data[str(i)]["unanswered"]]
    else:
        subset = [(i, q) for i, q in enumerate(questions)]

    if not subset:
        print("\n[No hay preguntas para este filtro. Volviendo al menú...]\n")
        press_any_key()
        return

    # random.shuffle(subset)  # Descomenta si deseas barajar

    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        resultado = preguntar(qid, qdata, perf_data)
        save_performance_data(perf_data)
        # Mostrar estadísticas después de cada pregunta
        print_scoreboard(questions, perf_data)

        if resultado is None:
            # usuario salió
            break
        idx += 1

    clear()
    print("La sesión de preguntas ha terminado.\n")
    press_any_key()

def comando_quiz_todos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="all")

def comando_quiz_sin_responder(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="unanswered")

def comando_quiz_erroneos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="wrong")

def comando_reseteo(perf_data):
    confirm = input("¿Estás seguro de resetear el progreso? (s/n) ").lower()
    if confirm == "s":
        perf_data.clear()
        save_performance_data(perf_data)
        print("Progreso reseteado con éxito.\n")
        press_any_key()

def comando_salir():
    print("¡Hasta luego!")
    sys.exit(0)

def main():
    clear()
    print(f"QuizProg v{VERSION} - Seguimiento continuo de estadísticas\n")

    questions, cursos_dict = load_all_quizzes()
    print_cursos_summary(cursos_dict)

    perf_data = load_performance_data()

    while True:
        clear()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("[1] Todas las preguntas")
        print("[2] Solo preguntas no respondidas")
        print("[3] Solo preguntas erróneas")
        print("[4] Resetear progreso")
        print("[5] Salir\n")

        choice = input("Selecciona una opción: ").strip()
        if choice == "1":
            comando_quiz_todos(questions, perf_data)
        elif choice == "2":
            comando_quiz_sin_responder(questions, perf_data)
        elif choice == "3":
            comando_quiz_erroneos(questions, perf_data)
        elif choice == "4":
            comando_reseteo(perf_data)
        elif choice == "5":
            comando_salir()
        else:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        print("\n[!] Saliendo (Ctrl+C)...")
        sys.exit(0)
    except Exception as e:
        clear()
        print("[!] Excepción no manejada:")
        traceback.print_exc()
        sys.exit(1)
