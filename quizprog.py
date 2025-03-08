import os
import json
import random
import sys
import traceback

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.2.1"

def clear():
    """Limpia la pantalla."""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    """Pausa: espera al usuario."""
    input("\nPresiona Enter para continuar...")

# ---------------------------------------------------------------------------
# CARGA Y ESTRUCTURA DE ARCHIVOS
# ---------------------------------------------------------------------------
def load_json_file(filepath):
    """Carga JSON de un archivo, o None si falla."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Error al cargar '{filepath}': {ex}")
        return None

def descubrir_quiz_files(folder):
    """Encuentra todos los .json en la carpeta recursivamente."""
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes():
    """
    Carga todos los .json bajo QUIZ_DATA_FOLDER.
    Devuelve:
      - combined_questions: lista global de todas las preguntas
      - cursos_dict: info para imprimir resumen
      - cursos_archivos: estructura para elegir curso/archivo

    cursos_archivos => {
      "administrativo2": {
         "rutaCompleta1.json": {
            "filename": "...",
            "questions": [...],
            "question_count": N
         },
         "rutaCompleta2.json": ...
      },
      "otrocurso": ...
    }
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

        # Determinar "curso" => la primera carpeta
        rel_path = os.path.relpath(filepath, QUIZ_DATA_FOLDER)
        parts = rel_path.split(os.sep)
        curso = parts[0]

        if curso not in cursos_dict:
            cursos_dict[curso] = []
        if curso not in cursos_archivos:
            cursos_archivos[curso] = {}

        filename_only = os.path.basename(filepath)

        # Para el resumen (cursos_dict):
        cursos_dict[curso].append({
            "filename": filename_only,
            "filepath": filepath,
            "question_count": file_question_count
        })

        # Para la estructura de curso->archivo
        cursos_archivos[curso][filepath] = {
            "filename": filename_only,
            "questions": [],
            "question_count": file_question_count
        }

        # Añadir a la lista global
        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)
                # También lo guardamos en cursos_archivos
                cursos_archivos[curso][filepath]["questions"].append(q)

    return combined_questions, cursos_dict, cursos_archivos

def print_cursos_summary(cursos_dict):
    """Imprime cuántos archivos y cuántas preguntas hay por curso."""
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

# ---------------------------------------------------------------------------
# GUARDAR/CARGAR DESEMPEÑO GLOBAL
# ---------------------------------------------------------------------------
def load_performance_data():
    """Carga datos de desempeño (wrong/unanswered)."""
    if not os.path.exists(PERFORMANCE_FILE):
        return {}
    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_performance_data(perf_data):
    """Guarda datos de desempeño en JSON."""
    try:
        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")

# ---------------------------------------------------------------------------
# MOSTRAR ESTADÍSTICAS GLOBALES SI SE DESEA
# ---------------------------------------------------------------------------
def print_scoreboard(questions, perf_data):
    """
    Estadísticas globales: cuántas correctas, erróneas, sin responder, total.
    (No se confunde con la "sesión local" de la run actual.)
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

    print(f"\n** Estadísticas globales: Correctas: {correct}, Erróneas: {wrong}, "
          f"Sin responder: {unanswered}, Total: {total} **\n")

# ---------------------------------------------------------------------------
# MOSTRAR RESUMEN LOCAL DE SESIÓN
# ---------------------------------------------------------------------------
def print_local_summary(session_counts):
    """
    Muestra un resumen de la sesión actual (correct/wrong/unanswered).
    """
    c = session_counts["correct"]
    w = session_counts["wrong"]
    u = session_counts["unanswered"]
    total = c + w + u

    print("\n=== Resumen de esta sesión ===")
    print(f"Correctas: {c}")
    print(f"Incorrectas: {w}")
    print(f"No respondidas (saltadas o confirmadas con 0): {u}")
    print(f"Total en esta sesión: {total}\n")
    press_any_key()

# ---------------------------------------------------------------------------
# PREGUNTAR: UNA SOLA PREGUNTA
# ---------------------------------------------------------------------------
def preguntar(qid, question_data, perf_data, session_counts):
    """
    Muestra UNA pregunta, randomiza las respuestas,
    y actualiza tanto perf_data como session_counts.
    Retorna:
      True  -> contada como "correcta"
      False -> contada como "incorrecta" (o "skip")
      None  -> usuario confirmó que quiere salir de la sesión
    """
    # Marca en perf_data si no existe
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear()

    question_text = question_data["question"]
    answers_original = question_data["answers"]
    answers_shuffled = answers_original[:]
    random.shuffle(answers_shuffled)  # randomiza la lista de respuestas

    explanation = question_data.get("explanation", "")
    wrongmsg = question_data.get("wrongmsg", "")

    # Muestra origen (archivo)
    source_path = question_data.get("_quiz_source", "")
    archivo_origen = os.path.basename(source_path) if source_path else ""
    if archivo_origen:
        print(f"(Pregunta de: {archivo_origen})\n")

    # Hallar posiciones correctas en la lista barajada
    correct_indices = [
        i for i, ans in enumerate(answers_shuffled)
        if ans.get("correct", False)
    ]
    if not correct_indices:
        print(f"[!] Pregunta {qid} sin respuestas correctas; se omite...\n")
        perf_data[str(qid)]["unanswered"] = False
        # La contamos como "correcta" para no complicar,
        # o podrías manejarlo de otra forma
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
        # Confirmar que realmente quiere salir
        clear()
        print("¿Seguro que deseas salir de esta sesión y volver al sub-menú? (s/n)")
        confirm = input("> ").lower()
        if confirm == "s":
            # Salir de la sesión => None
            return None
        else:
            # “No” => no salir, podemos considerarlo “unanswered”
            session_counts["unanswered"] += 1
            return False

    try:
        seleccion = [int(x) - 1 for x in opcion.split(",")]
    except ValueError:
        seleccion = [-1]

    # Verificar correct/incorrect
    if not multi_correct:
        # 1 sola respuesta correcta
        if len(seleccion) == 1 and seleccion[0] in correct_indices:
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
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False
    else:
        # Caso de respuestas múltiples
        correct_set = set(correct_indices)
        user_set = set(seleccion)
        if user_set == correct_set:
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
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False

# ---------------------------------------------------------------------------
# FUNCION PRINCIPAL PARA JUGAR UN QUIZ
# ---------------------------------------------------------------------------
def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    - filter_mode: "all", "unanswered", "wrong"
    - file_filter: None => todas, o un path => solo preguntas de ese archivo

    Después de terminar (o salir con 0->confirm),
    se imprime un RESUMEN LOCAL de la sesión. No volvemos al main menu,
    sino que regresamos a la función que llamó a play_quiz (e.g. sub-menú).
    """
    # Construir subset
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
        subset = all_pairs  # "all"

    if not subset:
        print("\n[No hay preguntas para este filtro. Volviendo...]\n")
        press_any_key()
        return

    # random.shuffle(subset)  # Descomentar si deseas barajar el orden de las preguntas

    # Contadores para esta SESIÓN local
    session_counts = {
        "correct": 0,
        "wrong": 0,
        "unanswered": 0
    }

    idx = 0
    while idx < len(subset):
        (qid, qdata) = subset[idx]
        resultado = preguntar(qid, qdata, perf_data, session_counts)
        if resultado is None:
            # Usuario decidió salir y confirmó => romper
            break

        save_performance_data(perf_data)
        # Si deseas mostrar scoreboard global en cada pregunta:
        # print_scoreboard(full_questions, perf_data)

        idx += 1

    # Muestra resumen local de esta sesión
    clear()
    print_local_summary(session_counts)

# ---------------------------------------------------------------------------
# COMANDOS PRINCIPALES
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
# ELEGIR UN ARCHIVO ESPECIFICO
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
            for idx, fp in enumerate(archivo_list, start=1):
                info = archivos_dict[fp]
                print(f"[{idx}] {info['filename']} ({info['question_count']} preguntas)")
            print("\n[0] Volver al listado de cursos\n")

            opcion_archivo = input("Elige un archivo: ").strip()
            if opcion_archivo == "0":
                # Volver a elegir curso
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
                # Sub-menú para elegir modo
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
                    continue

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    clear()
    print(f"QuizProg v{VERSION} - Todas las funcionalidades integradas\n")

    questions, cursos_dict, cursos_archivos = load_all_quizzes()
    print_cursos_summary(cursos_dict)

    perf_data = load_performance_data()

    while True:
        clear()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("1) Todas las preguntas (modo global)")
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

# ---------------------------------------------------------------------------
# EJECUCION
# ---------------------------------------------------------------------------
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
