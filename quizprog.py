import os
import json
import random
import sys
import traceback
import re

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.5.0"

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
    """Carga JSON, retorna None si falla."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Error al cargar '{filepath}': {ex}")
        return None

def descubrir_quiz_files(folder):
    """Encuentra recursivamente .json en la carpeta dada."""
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes():
    """
    Carga todos los JSON en QUIZ_DATA_FOLDER.
    Devuelve: 
      - combined_questions: todas las preguntas
      - cursos_dict: para resumen
      - cursos_archivos: para menú de curso/archivo
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

        # Determine "curso" by the first subfolder
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

        # Add to combined list
        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)
                cursos_archivos[curso][filepath]["questions"].append(q)

    return combined_questions, cursos_dict, cursos_archivos

def print_cursos_summary(cursos_dict):
    """Imprime cuántos archivos y preguntas hay por cada curso."""
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

# GLOBAL scoreboard is optional
def print_scoreboard_global(questions, perf_data):
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
# 1) Label original answers as 'a','b','c'... so we can parse references.
# 2) After shuffle, rewrite references in text, e.g. "a y c" => new letters.
# ---------------------------------------------------------------------------

LETTERS = "abcdefghijklmnopqrstuvwxyz"  # up to 26

def label_original_answers(answers):
    """
    Assign 'a','b','c', etc. to each answer in the original order.
    Store it in 'original_label' for reference rewriting.
    """
    for i, ans in enumerate(answers):
        if i < len(LETTERS):
            ans["original_label"] = LETTERS[i]
        else:
            # if more than 26 answers, we do something else or just skip
            ans["original_label"] = f'({i})'  # fallback

def rewrite_references(text, remap):
    """
    Replaces references in 'text' from original_label => new_label.
    e.g. if remap={'a':'C','b':'A','c':'B'} and text='a y c son correctas'
         => 'C y B son correctas'

    We'll do a simple regex to find word-bound references like
    \b[a-dA-D]\b or a) etc. (some heuristics).
    """
    # We'll try a simpler approach: we look for separate words or
    # small tokens of [a-z].
    # Then we replace them with the new label from remap if found.

    def replacer(match):
        # matched original letter in group(0)
        orig = match.group(0).lower()  # e.g. 'a'
        if orig in remap:
            return remap[orig]
        return match.group(0)  # else no change

    # We'll try capturing single letters or 'a)', 'b)', '(a)', etc.
    # This approach might not handle every edge case, but covers typical usage.
    pattern = re.compile(r"\b[a-z]\b|\([a-z]\)|[a-z]\)|\([a-z]\b", re.IGNORECASE)
    return pattern.sub(replacer, text)

def sanitize_question(question_data):
    """
    1) Assign original labels (a,b,c...) to each answer in 'answers'.
    2) If the question or other answers contain references to 'a, b, c, d', we rewrite them AFTER shuffle.
       We'll handle that in 'preguntar()' after we know the shuffle order.
    """
    # We do step 1 here: label each answer in original order
    # so we know how to parse references.
    label_original_answers(question_data["answers"])

# ---------------------------------------------------------------------------
# PREGUNTAR
# ---------------------------------------------------------------------------
def preguntar(qid, question_data, perf_data, session_counts):
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear()

    # We'll do the final shuffle here, then build a map from original_label => new label
    original_answers = question_data["answers"]  # has original_label
    answers_shuffled = original_answers[:]
    random.shuffle(answers_shuffled)

    # Now build "new_label_map": original 'a' => new letter 'A', etc.
    # e.g. if answers_shuffled[0].original_label=='c', that becomes new label 'A'
    new_label_map = {}
    for i, ans in enumerate(answers_shuffled):
        orig_label = ans["original_label"]  # 'a','b','c', etc
        # we'll use uppercase for the new label
        new_label = chr(ord('A') + i)  # 'A','B','C','D'...
        new_label_map[orig_label] = new_label

    # We'll rewrite references in the question text, explanation, answer texts themselves
    question_text = rewrite_references(question_data["question"], new_label_map)

    # We might also want to rewrite references in each answer's text if it references other answers.
    # e.g. if an answer says "a y c son correctas." We'll fix that too:
    for ans in answers_shuffled:
        ans["display_text"] = rewrite_references(ans["text"], new_label_map)

    explanation = question_data.get("explanation", "")
    explanation = rewrite_references(explanation, new_label_map)
    wrongmsg = question_data.get("wrongmsg", "")
    wrongmsg = rewrite_references(wrongmsg, new_label_map)

    # Find correct indices
    correct_indices = [i for i, ans in enumerate(answers_shuffled) if ans.get("correct", False)]
    if not correct_indices:
        print(f"[!] Pregunta {qid} sin respuestas correctas; se omite...\n")
        perf_data[str(qid)]["unanswered"] = False
        session_counts["correct"] += 1
        press_any_key()
        return True

    multi_correct = (len(correct_indices) > 1)

    # Print source
    source_path = question_data.get("_quiz_source", "")
    archivo_origen = os.path.basename(source_path) if source_path else ""
    if archivo_origen:
        print(f"(Pregunta de: {archivo_origen})\n")

    print(f"Pregunta {qid}:\n{question_text}\n")

    # Print the shuffled answers with new labels
    for i, ans in enumerate(answers_shuffled):
        new_label = chr(ord('A') + i)
        print(f"[{new_label}] {ans['display_text']}")

    print("\n[0] Salir de la sesión\n")
    if multi_correct:
        print("Puede haber varias respuestas correctas. Ej: 'A,C'")

    opcion = input("Tu respuesta: ").strip().upper()
    if opcion == "0":
        clear()
        print("¿Seguro que deseas salir de esta sesión y volver al sub-menú? (s/n)")
        confirm = input("> ").lower()
        if confirm == "s":
            return None
        else:
            session_counts["unanswered"] += 1
            return False

    # Convert letters to indices
    user_positions = []
    try:
        parts = opcion.split(",")
        for p in parts:
            p = p.strip()
            if not p:
                continue
            idx = ord(p) - ord('A')  # 'A'->0
            user_positions.append(idx)
    except ValueError:
        user_positions = [-1]

    # Evaluate correctness
    perf_data_entry = perf_data[str(qid)]
    if not multi_correct:
        if len(user_positions) == 1 and user_positions[0] in correct_indices:
            # correct
            perf_data_entry["unanswered"] = False
            perf_data_entry["wrong"] = False
            session_counts["correct"] += 1
            clear()
            print("¡CORRECTO!\n")
            if explanation:
                print("EXPLICACIÓN:\n" + explanation + "\n")
            press_any_key()
            return True
        else:
            # incorrect
            perf_data_entry["unanswered"] = False
            perf_data_entry["wrong"] = True
            session_counts["wrong"] += 1
            clear()
            print("¡INCORRECTO!\n")
            if wrongmsg:
                print(wrongmsg + "\n")
            if explanation:
                print("EXPLICACIÓN:\n" + explanation + "\n")
            press_any_key()
            return False
    else:
        correct_set = set(correct_indices)
        user_set = set(user_positions)
        if user_set == correct_set:
            perf_data_entry["unanswered"] = False
            perf_data_entry["wrong"] = False
            session_counts["correct"] += 1
            clear()
            print("¡CORRECTO!\n")
            if explanation:
                print("EXPLICACIÓN:\n" + explanation + "\n")
            press_any_key()
            return True
        else:
            perf_data_entry["unanswered"] = False
            perf_data_entry["wrong"] = True
            session_counts["wrong"] += 1
            clear()
            print("¡INCORRECTO!\n")
            if wrongmsg:
                print(wrongmsg + "\n")
            if explanation:
                print("EXPLICACIÓN:\n" + explanation + "\n")
            press_any_key()
            return False

def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    filter_mode in ["all","unanswered","wrong"]
    file_filter: if not None => only questions with _quiz_source == file_filter
    """
    # We'll label each question's answers with a,b,c... so we can parse references
    # This should happen once, so let's do it for each question before we filter:
    for q in full_questions:
        if not hasattr(q, "_labeled"):  # or use a custom key
            # "sanitize" or label answers in original order
            label_original_answers(q["answers"])  # or see sanitize_question approach
            q["_labeled"] = True

    # Build subset
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

    # random.shuffle(subset) # optional if you want to randomize question order

    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}
    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        resultado = preguntar(qid, qdata, perf_data, session_counts)
        if resultado is None:
            break
        save_performance_data(perf_data)
        idx += 1

    clear()
    print_local_summary(session_counts)

# ---------------------------------------------------------------------------
# COMANDOS
# ---------------------------------------------------------------------------
def comando_quiz_todos(questions, perf_data):
    play_quiz(questions, perf_data, "all", None)

def comando_quiz_sin_responder(questions, perf_data):
    play_quiz(questions, perf_data, "unanswered", None)

def comando_quiz_erroneos(questions, perf_data):
    play_quiz(questions, perf_data, "wrong", None)

def comando_reseteo(perf_data):
    confirm = input("¿Estás seguro de resetear el progreso? (s/n) ").lower()
    if confirm == "s":
        perf_data.clear()
        save_performance_data(perf_data)
        print("Progreso reseteado.\n")
        press_any_key()

def comando_salir():
    print("¡Hasta luego!")
    sys.exit(0)

def comando_elegir_archivo(questions, perf_data, cursos_archivos):
    curso_list = sorted(cursos_archivos.keys())
    if not curso_list:
        print("No hay cursos.")
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
                print(f"Has elegido: Curso '{chosen_curso}' / Archivo '{archivos_dict[chosen_file]['filename']}'\n")
                print("[1] Todas las preguntas de este archivo")
                print("[2] Solo no respondidas de este archivo")
                print("[3] Solo las que estén mal en este archivo")
                print("[4] Volver a elegir archivo\n")

                mode_choice = input("Elige un modo: ").strip()
                if mode_choice == "4":
                    break
                elif mode_choice == "1":
                    play_quiz(questions, perf_data, "all", chosen_file)
                elif mode_choice == "2":
                    play_quiz(questions, perf_data, "unanswered", chosen_file)
                elif mode_choice == "3":
                    play_quiz(questions, perf_data, "wrong", chosen_file)
                else:
                    pass

def main():
    clear()
    print(f"QuizProg v{VERSION} - Manteniendo referencias a 'a y c' tras shuffle\n")

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
        print("\n[!] Saliendo (Ctrl+C)...")
        sys.exit(0)
    except Exception as e:
        clear()
        print("[!] Excepción no manejada:")
        traceback.print_exc()
        sys.exit(1)