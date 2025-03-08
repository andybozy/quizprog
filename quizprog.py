import os
import json
import random
import sys
import traceback

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.1.2"

def clear():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    input("\nPresiona Enter para continuar...")

def load_json_file(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Error al cargar '{filepath}': {ex}")
        return None

def descubrir_quiz_files(folder):
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes():
    all_files = descubrir_quiz_files(QUIZ_DATA_FOLDER)
    if not all_files:
        print(f"No se encontraron archivos JSON en '{QUIZ_DATA_FOLDER}'!")
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

        # Determinar el “curso” por la primera subcarpeta
        rel_path = os.path.relpath(filepath, QUIZ_DATA_FOLDER)
        parts = rel_path.split(os.sep)
        curso = parts[0]

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

        # Combinar todas las preguntas en “combined_questions”
        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)
                # Guardar también en cursos_archivos
                cursos_archivos[curso][filepath]["questions"].append(q)

    return combined_questions, cursos_dict, cursos_archivos

def print_cursos_summary(cursos_dict):
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
    if not os.path.exists(PERFORMANCE_FILE):
        return {}
    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_performance_data(perf_data):
    try:
        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")

def print_scoreboard(questions, perf_data):
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

def preguntar(qid, question_data, perf_data):
    """
    Muestra una pregunta con respuestas barajadas (opcional).
    Retorna:
      True  -> correcto
      False -> incorrecto
      None  -> salir

    Ahora: la 'explanation' (si existe) se muestra tanto en correctas como en erróneas.
    """
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear()

    question_text = question_data["question"]

    # Barajar respuestas si se desea:
    answers_original = question_data["answers"]
    answers_shuffled = answers_original[:]
    random.shuffle(answers_shuffled)

    # Tomamos la explicación (razón) de la pregunta
    explanation = question_data.get("explanation", "")
    wrongmsg = question_data.get("wrongmsg", "")

    source_path = question_data.get("_quiz_source", "")
    archivo_origen = os.path.basename(source_path) if source_path else ""
    if archivo_origen:
        print(f"(Pregunta de: {archivo_origen})\n")

    # Hallar los índices correctos
    correct_indices = [
        i for i, ans in enumerate(answers_shuffled)
        if ans.get("correct", False)
    ]
    if not correct_indices:
        print(f"[!] Pregunta {qid} sin respuestas correctas; se omite...\n")
        perf_data[str(qid)]["unanswered"] = False
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
        perf_data[str(qid)]["unanswered"] = True
        return None

    try:
        seleccion = [int(x) - 1 for x in opcion.split(",")]
    except ValueError:
        seleccion = [-1]

    # Revisar si es correcto o no
    if not multi_correct:
        if len(seleccion) == 1 and seleccion[0] in correct_indices:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            clear()
            print("¡CORRECTO!\n")
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("¡INCORRECTO!\n")
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
    else:
        # Varias respuestas correctas
        correct_set = set(correct_indices)
        user_set = set(seleccion)
        if user_set == correct_set:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            clear()
            print("¡CORRECTO!\n")
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("¡INCORRECTO!\n")
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")

    # Muestra la explicación, aunque sea errónea la respuesta
    if explanation:
        print("EXPLICACIÓN:\n" + explanation + "\n")

    press_any_key()

    # Retornamos True o False (correcto / incorrecto)
    return not perf_data[str(qid)]["wrong"]

def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    filter_mode en ["all", "unanswered", "wrong"]
    file_filter: si no es None, filtra preguntas de un solo archivo.
    """
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
        print("\n[No hay preguntas para este filtro. Volviendo al menú...]\n")
        press_any_key()
        return

    # random.shuffle(subset)  # <--- Descomenta para barajar el orden de las preguntas

    idx = 0
    while idx < len(subset):
        (qid, qdata) = subset[idx]
        resultado = preguntar(qid, qdata, perf_data)
        save_performance_data(perf_data)
        print_scoreboard(full_questions, perf_data)

        if resultado is None:  # usuario salió
            break
        idx += 1

    clear()
    print("La sesión de preguntas ha terminado.\n")
    press_any_key()

def comando_quiz_todos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="all", file_filter=None)

def comando_quiz_sin_responder(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=None)

def comando_quiz_erroneos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="wrong", file_filter=None)

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

def comando_elegir_archivo(questions, perf_data, cursos_archivos):
    curso_list = sorted(cursos_archivos.keys())
    if not curso_list:
        print("No hay cursos disponibles.")
        press_any_key()
        return

    clear()
    print("CURSOS DISPONIBLES:\n")
    for idx, c in enumerate(curso_list, start=1):
        print(f"[{idx}] {c}")

    print("\n[0] Cancelar\n")
    opcion_curso = input("Elige un curso: ").strip()
    if opcion_curso == "0":
        return
    try:
        curso_idx = int(opcion_curso) - 1
        if curso_idx < 0 or curso_idx >= len(curso_list):
            return
    except:
        return

    chosen_curso = curso_list[curso_idx]
    archivos_dict = cursos_archivos[chosen_curso]
    archivo_list = list(archivos_dict.keys())
    if not archivo_list:
        print("No hay archivos en este curso.")
        press_any_key()
        return

    clear()
    print(f"ARCHIVOS EN CURSO: {chosen_curso}\n")
    for idx, fp in enumerate(archivo_list, start=1):
        info = archivos_dict[fp]
        print(f"[{idx}] {info['filename']} ({info['question_count']} preguntas)")

    print("\n[0] Cancelar\n")
    opcion_archivo = input("Elige un archivo: ").strip()
    if opcion_archivo == "0":
        return
    try:
        archivo_idx = int(opcion_archivo) - 1
        if archivo_idx < 0 or archivo_idx >= len(archivo_list):
            return
    except:
        return

    chosen_file = archivo_list[archivo_idx]

    while True:
        clear()
        print(f"Has elegido el curso '{chosen_curso}' / archivo '{archivos_dict[chosen_file]['filename']}'\n")
        print("[1] Todas las preguntas de este archivo")
        print("[2] Solo no respondidas de este archivo")
        print("[3] Solo las que estén mal en este archivo")
        print("[4] Cancelar\n")

        mode_choice = input("Elige un modo: ").strip()
        if mode_choice == "4":
            return
        elif mode_choice == "1":
            play_quiz(questions, perf_data, filter_mode="all", file_filter=chosen_file)
            break
        elif mode_choice == "2":
            play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=chosen_file)
            break
        elif mode_choice == "3":
            play_quiz(questions, perf_data, filter_mode="wrong", file_filter=chosen_file)
            break
        else:
            pass

def main():
    clear()
    print(f"QuizProg v{VERSION} - Respuestas en orden aleatorio\n")

    questions, cursos_dict, cursos_archivos = load_all_quizzes()
    print_cursos_summary(cursos_dict)

    perf_data = load_performance_data()

    while True:
        clear()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("[1] Todas las preguntas (global)")
        print("[2] Solo preguntas no respondidas (global)")
        print("[3] Solo preguntas erróneas (global)")
        print("[4] Elegir un curso y archivo específico")
        print("[5] Resetear progreso")
        print("[6] Salir\n")

        choice = input("Selecciona una opción: ").strip()
        if choice == "1":
            comando_quiz_todos(questions, perf_data)
        elif choice == "2":
            comando_quiz_sin_responder(questions, perf_data)
        elif choice == "3":
            comando_quiz_erroneos(questions, perf_data)
        elif choice == "4":
            comando_elegir_archivo(questions, perf_data, cursos_archivos)
        elif choice == "5":
            comando_reseteo(perf_data)
        elif choice == "6":
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
