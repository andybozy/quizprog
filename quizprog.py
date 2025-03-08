import os
import json
import random
import sys
import traceback

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.0.2"

# ---------------------------------------------------------------------------
# LIMPIEZA DE PANTALLA Y ENTRADA
# ---------------------------------------------------------------------------
def clear():
    """Limpia la pantalla, independientemente del sistema operativo."""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    """Pausa: espera que el usuario presione Enter."""
    input("\nPresiona Enter para continuar...")

# ---------------------------------------------------------------------------
# FUNCIONES PARA CARGAR DATOS
# ---------------------------------------------------------------------------
def load_json_file(filepath):
    """Carga y devuelve el contenido de un archivo JSON, o None si falla."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Error al cargar '{filepath}': {ex}")
        return None

def descubrir_quiz_files(folder):
    """
    Recorre recursivamente la carpeta `folder` (quiz_data) para encontrar
    todos los archivos .json. Devuelve una lista de rutas completas (paths).
    """
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

# ---------------------------------------------------------------------------
# AGRUPAR POR CURSOS
# ---------------------------------------------------------------------------
def load_all_quizzes():
    """
    Carga y une todos los archivos JSON encontrados en QUIZ_DATA_FOLDER.
    A la vez, agrupa cada archivo en un diccionario por "curso" (subcarpeta).

    Devuelve:
      - combined_questions: lista total de todas las preguntas (dicts)
      - cursos_dict: p.ej.
        {
          "administrativo2": [
            {"filename": "...", "filepath": "...", "question_count": N}, ...
          ],
          "otrocurso": [...],
          ...
        }
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
            # Omite archivos que no tengan estructura "questions"
            continue

        questions_list = data["questions"]
        file_question_count = len(questions_list)

        # Determinar el "curso" a partir de la subcarpeta
        rel_path = os.path.relpath(filepath, QUIZ_DATA_FOLDER)
        # Por ejemplo: "administrativo2\test.json" → partes = ["administrativo2", "test.json"]
        parts = rel_path.split(os.sep)
        curso = parts[0]  # El primer segmento se toma como el nombre del curso

        if curso not in cursos_dict:
            cursos_dict[curso] = []

        filename_only = os.path.basename(filepath)

        cursos_dict[curso].append({
            "filename": filename_only,
            "filepath": filepath,
            "question_count": file_question_count
        })

        # Combinar estas preguntas a la lista global
        for q in questions_list:
            # Verificar que tenga la estructura "question" y "answers"
            if "question" in q and "answers" in q:
                # Guardar referencia opcional (origen)
                q["_quiz_source"] = filepath
                combined_questions.append(q)

    return combined_questions, cursos_dict

def print_cursos_summary(cursos_dict):
    """
    Muestra un resumen en pantalla indicando cuántos archivos y preguntas
    hay por cada 'curso'.
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

        # Si deseas mostrar cada archivo dentro del curso:
        for info in files_info:
            print(f"   • {info['filename']} ({info['question_count']} preguntas)")
        print()  # línea en blanco

    print(f"** Total: {total_archivos} archivos, {total_preguntas} preguntas en total **\n")
    press_any_key()

# ---------------------------------------------------------------------------
# GUARDAR / CARGAR DATOS DE DESEMPEÑO
# ---------------------------------------------------------------------------
def load_performance_data():
    """Carga (o inicializa) el archivo PERFORMANCE_FILE para marcar errores / sin responder."""
    if not os.path.exists(PERFORMANCE_FILE):
        return {}
    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_performance_data(perf_data):
    """Guarda los datos de desempeño en PERFORMANCE_FILE."""
    try:
        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")

# ---------------------------------------------------------------------------
# LÓGICA PARA PREGUNTAR
# ---------------------------------------------------------------------------
def preguntar(qid, question_data, perf_data):
    """
    Muestra una pregunta y retorna:
      True  -> respondida correctamente
      False -> respondida incorrectamente
      None  -> el usuario decide salir
    Actualiza perf_data con flags ("wrong", "unanswered").
    """
    # Marcamos la pregunta como sin responder por defecto:
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear()

    question_text = question_data["question"]
    answers = question_data["answers"]  # lista de { "text": str, "correct": bool }
    explanation = question_data.get("explanation", "")
    wrongmsg = question_data.get("wrongmsg", "")

    # Indicar los índices de las respuestas correctas:
    correct_indices = [i for i, ans in enumerate(answers) if ans.get("correct")]
    if not correct_indices:
        # Si no hay respuestas correctas, omitir
        print(f"[!] La pregunta {qid} no tiene respuestas correctas. Se omite...\n")
        perf_data[str(qid)]["unanswered"] = False
        return True

    multi_correct = (len(correct_indices) > 1)

    print(f"Pregunta {qid}:\n{question_text}\n")
    for i, ans in enumerate(answers):
        print(f"[{i+1}] {ans['text']}")
    print("\n[0] Salir de la sesión de quiz\n")

    if multi_correct:
        print("Atención: Puede haber varias respuestas correctas.\n"
              "Escribe todos los números correctos separados por coma (ej. '1,3').\n")

    opcion = input("Tu respuesta: ").strip()
    if opcion == "0":
        perf_data[str(qid)]["unanswered"] = True
        return None  # usuario sale

    try:
        seleccion = [int(x) - 1 for x in opcion.split(",")]
    except ValueError:
        seleccion = [-1]  # forzar respuesta incorrecta

    if not multi_correct:
        # Caso de una sola respuesta correcta
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
        # Caso de respuestas múltiples
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

# ---------------------------------------------------------------------------
# FUNCIONES / COMANDOS DEL MENÚ PRINCIPAL
# ---------------------------------------------------------------------------
def comando_quiz_todos(questions, perf_data):
    """Jugar con todas las preguntas."""
    play_quiz(questions, perf_data, filter_mode="all")

def comando_quiz_sin_responder(questions, perf_data):
    """Jugar sólo con preguntas no respondidas aún."""
    play_quiz(questions, perf_data, filter_mode="unanswered")

def comando_quiz_erroneos(questions, perf_data):
    """Jugar sólo con las preguntas contestadas mal."""
    play_quiz(questions, perf_data, filter_mode="wrong")

def comando_reseteo(perf_data):
    """Reiniciar todo el progreso de desempeño."""
    confirm = input("¿Seguro que deseas resetear el progreso? (s/n) ").lower()
    if confirm == "s":
        perf_data.clear()
        save_performance_data(perf_data)
        print("Progreso reseteado con éxito.\n")
        press_any_key()

def comando_salir():
    """Salir del programa."""
    print("¡Hasta la próxima!")
    sys.exit(0)

# ---------------------------------------------------------------------------
# LÓGICA GENERAL DE LA SESIÓN
# ---------------------------------------------------------------------------
def play_quiz(questions, perf_data, filter_mode="all"):
    """
    filter_mode:
      - "all": todas las preguntas
      - "unanswered": sólo no respondidas
      - "wrong": sólo las respondidas mal
    """
    if filter_mode == "wrong":
        subset = [(i, q) for i, q in enumerate(questions)
                  if str(i) in perf_data and perf_data[str(i)]["wrong"]]
    elif filter_mode == "unanswered":
        subset = [(i, q) for i, q in enumerate(questions)
                  if str(i) not in perf_data or perf_data[str(i)]["unanswered"]]
    else:
        # "all"
        subset = [(i, q) for i, q in enumerate(questions)]

    if not subset:
        print("\n[No hay preguntas para este filtro. Regresando al menú...]\n")
        press_any_key()
        return

    # Si deseas barajar el orden de las preguntas, descomenta:
    # random.shuffle(subset)

    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        resultado = preguntar(qid, qdata, perf_data)
        save_performance_data(perf_data)  # guarda tras cada pregunta
        if resultado is None:
            # usuario salió
            break
        idx += 1

    clear()
    print("La sesión de preguntas ha terminado.\n")
    press_any_key()

# ---------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ---------------------------------------------------------------------------
def main():
    clear()
    print(f"QuizProg v{VERSION} - Carga automática de quizzes\n")

    # 1) Cargar todos los quizzes y agrupar por 'curso'
    questions, cursos_dict = load_all_quizzes()

    # 2) Mostrar resumen de cursos (carpetas) y sus archivos/preguntas
    print_cursos_summary(cursos_dict)

    # 3) Cargar/crear datos de desempeño
    perf_data = load_performance_data()

    # 4) Menú principal
    while True:
        clear()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("[1] Todas las preguntas")
        print("[2] Solo preguntas no respondidas")
        print("[3] Solo preguntas con errores previos")
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

# ---------------------------------------------------------------------------
# PUNTO DE ENTRADA
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        print("\n[!] Saliendo por interrupción con Ctrl+C...")
        sys.exit(0)
    except Exception as e:
        clear()
        print("[!] Excepción no manejada:")
        traceback.print_exc()
        sys.exit(1)
