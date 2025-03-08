import os
import json
import random
import sys
import traceback

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.4.0"

def clear():
    """Limpia la pantalla (Windows/Unix)."""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    """Pausa hasta que el usuario presione Enter."""
    input("\nPresiona Enter para continuar...")

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

def load_all_quizzes():
    """
    1) Carga todos los .json en QUIZ_DATA_FOLDER.
    2) Retorna:
       - combined_questions: lista con TODAS las preguntas
       - cursos_dict: para el resumen
       - cursos_archivos: para elegir curso/archivo
    """
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

        # Determinar el curso por la primera subcarpeta
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

        # Agregar a combined_questions y al dict curso->archivo
        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)
                cursos_archivos[curso][filepath]["questions"].append(q)

    return combined_questions, cursos_dict, cursos_archivos

def print_cursos_summary(cursos_dict):
    """Muestra cuántos archivos y preguntas hay por cada curso."""
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
    """Carga (o crea) el archivo PERFORMANCE_FILE con info global de desempeño."""
    if not os.path.exists(PERFORMANCE_FILE):
        return {}
    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_performance_data(perf_data):
    """Guarda datos de desempeño en PERFORMANCE_FILE."""
    try:
        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")

def print_scoreboard_global(questions, perf_data):
    """Muestra estadísticas globales (correct, wrong, unanswered, total)."""
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

    print(f"\n** Estadísticas globales: Correctas: {correct}, Erróneas: {wrong}, "
          f"Sin responder: {unanswered}, Total: {total} **\n")

def print_local_summary(session_counts):
    """
    Resume la sesión actual: correct, wrong, unanswered.
    """
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

# ---------------------------------------------------------------------------
# PREGUNTAR: UNA SOLA PREGUNTA, RESPUESTAS BARAJADAS, LABELS CON LETRAS
# ---------------------------------------------------------------------------
def preguntar(qid, question_data, perf_data, session_counts):
    """
    Muestra una pregunta:
      - Shuffle answers
      - Label answers with letters [A], [B], [C], etc.
      - Devuelve True/False/None
        True  => correcto
        False => incorrecto
        None  => usuario confirmó "salir"
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

    # Origen del archivo
    source_path = question_data.get("_quiz_source", "")
    archivo_origen = os.path.basename(source_path) if source_path else ""
    if archivo_origen:
        print(f"(Pregunta de: {archivo_origen})\n")

    # Identificar índices correctos
    correct_indices = [i for i, ans in enumerate(answers_shuffled) if ans.get("correct", False)]
    if not correct_indices:
        print(f"[!] Pregunta {qid} sin respuestas correctas; se omite...\n")
        perf_data[str(qid)]["unanswered"] = False
        session_counts["correct"] += 1  # o ajusta la lógica a tu gusto
        return True

    multi_correct = (len(correct_indices) > 1)

    print(f"Pregunta {qid}:\n{question_text}\n")

    # Label letters: A, B, C, D, ...
    LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i, ans in enumerate(answers_shuffled):
        label = LETTERS[i]  # e.g. 'A', 'B', 'C' ...
        print(f"[{label}] {ans['text']}")

    print("\n[0] Salir de la sesión\n")
    if multi_correct:
        print("Puede haber varias respuestas correctas. Ejemplo: 'A,C'")

    # Esperar la respuesta
    opcion = input("Tu respuesta: ").strip().upper()
    if opcion == "0":
        # Confirmar salida
        clear()
        print("¿Seguro que deseas salir de esta sesión y volver al sub-menú? (s/n)")
        confirm = input("> ").lower()
        if confirm == "s":
            return None
        else:
            session_counts["unanswered"] += 1
            return False

    # Procesar la entrada. Puede ser 'A' o 'A,C'
    # Conviértelo a índices: 'A' => 0, 'B' => 1, etc.
    user_positions = []
    try:
        parts = opcion.split(",")
        for p in parts:
            p = p.strip()
            if not p:
                continue
            idx = ord(p) - ord('A')  # 'A' -> 0, 'B' -> 1, ...
            user_positions.append(idx)
    except ValueError:
        user_positions = [-1]

    # Verificar correct/incorrect
    if not multi_correct:
        # caso 1 sola respuesta
        if len(user_positions) == 1 and user_positions[0] in correct_indices:
            # Correcto
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            session_counts["correct"] += 1

            clear()
            print("¡CORRECTO!\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return True
        else:
            # Incorrecto
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            session_counts["wrong"] += 1

            clear()
            print("¡INCORRECTO!\n")
            if wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False
    else:
        # varias correctas
        correct_set = set(correct_indices)
        user_set = set(user_positions)
        if user_set == correct_set:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            session_counts["correct"] += 1

            clear()
            print("¡CORRECTO!\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return True
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            session_counts["wrong"] += 1

            clear()
            print("¡INCORRECTO!\n")
            if wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False

# ---------------------------------------------------------------------------
# BUCLE DE PREGUNTAS / SESIÓN
# ---------------------------------------------------------------------------
def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    filter_mode: "all", "unanswered", "wrong"
    file_filter: si no es None => solo preguntas con _quiz_source == file_filter
    """
    all_pairs = [(i, q) for i, q in enumerate(full_questions)]
    if file_filter is not None:
        all_pairs = [(i, q) for (i, q) in all_pairs if q.get("_quiz_source") == file_filter]

    if filter_mode == "wrong":
        subset = [(i, q) for (i, q) in all_pairs if str(i) in perf_data and perf_data[str(i)]["wrong"]]
    elif filter_mode == "unanswered":
        subset = [(i, q) for (i, q) in all_pairs if str(i) not in perf_data or perf_data[str(i)]["unanswered"]]
    else:
        subset = all_pairs  # "all"

    if not subset:
        print("\n[No hay preguntas para este filtro. Volviendo...]\n")
        press_any_key()
        return

    # random.shuffle(subset)  # Descomenta si deseas barajar el orden de las preguntas

    # Contadores LOCALES para la sesión actual
    session_counts = {
        "correct": 0,
        "wrong": 0,
        "unanswered": 0
    }

    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        resultado = preguntar(qid, qdata, perf_data, session_counts)
        if resultado is None:
            # Usuario decidió salir => romper
            break

        save_performance_data(perf_data)
        idx += 1

    # Al terminar, mostrar resumen local
    clear()
    print_local_summary(session_counts)

# ---------------------------------------------------------------------------
# MENÚS / COMANDOS
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# ELEGIR CURSO/ARCHIVO
# ---------------------------------------------------------------------------
def comando_elegir_archivo(questions, perf_data, cursos_archivos):
    curso_list = sorted(cursos_archivos.keys())
    if not curso_list:
        print("No hay cursos disponibles.")
        press_any_key()
        return

    while True:
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
                continue
        except:
            continue

        chosen_curso = curso_list[curso_idx]
        archivos_dict = cursos_archivos[chosen_curso]
        archivo_list = list(archivos_dict.keys())
        if not archivo_list:
            print("No hay archivos en este curso.")
            press_any_key()
            continue

        while True:
            clear()
            print(f"ARCHIVOS EN CURSO: {chosen_curso}\n")
            for i, fp in enumerate(archivo_list, start=1):
                info = archivos_dict[fp]
                print(f"[{i}] {info['filename']} ({info['question_count']} preguntas)")
            print("\n[0] Volver al listado de cursos\n")

            opcion_archivo = input("Elige un archivo: ").strip()
            if opcion_archivo == "0":
                # volver a elegir curso
                break

            try:
                archivo_idx = int(opcion_archivo) - 1
                if archivo_idx < 0 or archivo_idx >= len(archivo_list):
                    continue
            except:
                continue

            chosen_file = archivo_list[archivo_idx]

            while True:
                clear()
                print(f"Has elegido el curso '{chosen_curso}' / archivo '{archivos_dict[chosen_file]['filename']}'\n")
                print("[1] Todas las preguntas de este archivo")
                print("[2] Solo no respondidas de este archivo")
                print("[3] Solo las que estén mal en este archivo")
                print("[4] Volver a elegir archivo\n")

                mode_choice = input("Elige un modo: ").strip()
                if mode_choice == "4":
                    break
                elif mode_choice == "1":
                    play_quiz(questions, perf_data, filter_mode="all", file_filter=chosen_file)
                elif mode_choice == "2":
                    play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=chosen_file)
                elif mode_choice == "3":
                    play_quiz(questions, perf_data, filter_mode="wrong", file_filter=chosen_file)
                else:
                    pass

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    clear()
    print(f"QuizProg v{VERSION} - Respuestas barajadas con letras\n")

    questions, cursos_dict, cursos_archivos = load_all_quizzes()
    print_cursos_summary(cursos_dict)

    perf_data = load_performance_data()

    while True:
        clear()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("1) Todas las preguntas (global)")
        print("2) Solo preguntas no respondidas (global)")
        print("3) Solo preguntas erróneas (global)")
        print("4) Elegir un curso y archivo específico")
        print("5) Resetear progreso global")
        print("6) Salir\n")

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
        print("\n[!] Saliendo por Ctrl+C...")
        sys.exit(0)
    except Exception as e:
        clear()
        print("[!] Excepción no manejada:")
        traceback.print_exc()
        sys.exit(1)