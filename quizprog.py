import os
import json
import random
import sys
import traceback
import re

QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "3.0.0"

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
    """
    Returns:
      - combined_questions
      - cursos_dict (for summary)
      - cursos_archivos
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

        # Identify "curso"
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

        for q in questions_list:
            if "question" in q and "answers" in q:
                q["_quiz_source"] = filepath
                combined_questions.append(q)
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

LETTERS = "abcdefghijklmnopqrstuvwxyz"

def label_original_answers(q):
    """
    For each question, we label answers with 'original_label' = a,b,c,d...
    Also parse if the answer references something like "a y c" to store that in a 'refs' set.
    Then we'll see if that referencing answer is actually correct if those references are correct.
    """
    # If we already labeled, skip
    if "_labeled" in q:
        return
    answers = q["answers"]

    for i, ans in enumerate(answers):
        # label original
        if i < len(LETTERS):
            ans["original_label"] = LETTERS[i]  # 'a','b','c'...
        else:
            ans["original_label"] = f"({i})"

        # parse references
        # e.g. if text is "a y c son correctas"
        # we find references to single-letter tokens
        ans["refs"] = set()
        # We'll look for something like \b[a-d]\b
        # but let's keep it broad: \b[a-z]\b or \(a\)
        pattern = re.compile(r"\b[a-z]\b", re.IGNORECASE)
        found = pattern.findall(ans["text"])
        # store them in lower
        ans["refs"] = {f.lower() for f in found if f.lower() in LETTERS}

    q["_labeled"] = True

def is_answer_actually_correct(q, ans):
    """
    "ans" might have "refs" = { 'a','c',... }.
    This means "ans" claims those original_label answers are correct.

    We check if all those references are indeed correct in the original data.
    Then we combine with ans's own "correct" field (maybe it's explicitly correct or false).
    You can define your own rule. Example:
      - If 'refs' is not empty, we only treat this as correct if all the referenced answers are truly correct.
      - If the answer text also has "correct": true, we might combine the logic (like "AND").

    We'll do a logic:
      final_correct = ans["correct"] OR (all referenced are correct)
      or
      final_correct = ans["correct"] OR
         if 'refs' is not empty => all those references are correct answers in the question
    """
    # We'll read "correct" in the raw JSON:
    base_correct = ans.get("correct", False)
    # If no references, return base_correct
    if not ans["refs"]:
        return base_correct

    # If refs exist, check if all those references are actually correct answers
    # in the same question. For that, we see which answers have "correct": True
    # or do we do a "deep parse"? We'll do a simpler approach: the original "correct" field for that referenced letter is True.

    # Build a map label->correct from the question's answers
    label_map = {}
    for a in q["answers"]:
        lbl = a["original_label"]  # 'a','b'...
        # if a has references too, that might be meta. We won't go fully recursive for now.
        # We'll just read a["correct"]
        label_map[lbl] = a.get("correct", False)

    # check if all references are correct in that map
    all_ref_correct = True
    for r in ans["refs"]:
        if not label_map.get(r, False):
            all_ref_correct = False
            break

    final_correct = base_correct or all_ref_correct
    return final_correct

def rewrite_ref_text_to_new_labels(text, label_map):
    """Replace 'a','b','c' with new uppercase letters based on label_map."""
    if not text:
        return text

    def replacer(m):
        orig = m.group(0).lower()  # e.g. 'a'
        if orig in label_map:
            return label_map[orig]
        return m.group(0)

    pattern = re.compile(r"\b[a-z]\b", re.IGNORECASE)
    new_text = pattern.sub(replacer, text)
    return new_text

def preguntar(qid, question_data, perf_data, session_counts):
    # mark question_data with label_original_answers if needed
    label_original_answers(question_data)

    # We'll shuffle the question's answers. But we also need to see which are "actually correct" at runtime.
    # So let's build a final list with updated correctness.
    # 1) We'll build an array of "final_correct" for each answer, derived from the advanced logic:
    final_answer_data = []
    for ans in question_data["answers"]:
        actual_correct = is_answer_actually_correct(question_data, ans)
        final_answer_data.append({
            "orig_label": ans["original_label"],
            "text": ans["text"],
            "explanation": question_data.get("explanation",""),
            "wrongmsg": question_data.get("wrongmsg",""),
            "actual_correct": actual_correct
        })

    # 2) shuffle
    answers_shuffled = final_answer_data[:]
    random.shuffle(answers_shuffled)

    # 3) build a map from original_label -> new label [A],[B], ...
    new_label_map = {}
    for i, adata in enumerate(answers_shuffled):
        new_label = chr(ord('A') + i)
        new_label_map[adata["orig_label"]] = new_label

    # We'll rewrite references in the final answer text to reflect the new letters
    for adata in answers_shuffled:
        # rewrite any references in the text itself
        adata["display_text"] = rewrite_ref_text_to_new_labels(adata["text"], new_label_map)

    # also rewrite references in explanation / wrongmsg if needed
    explanation = question_data.get("explanation","")
    explanation = rewrite_ref_text_to_new_labels(explanation, new_label_map)
    wrongmsg = question_data.get("wrongmsg","")
    wrongmsg = rewrite_ref_text_to_new_labels(wrongmsg, new_label_map)

    # 4) find correct indices in the new shuffled array
    correct_indices = [i for i, adata in enumerate(answers_shuffled) if adata["actual_correct"]]
    multi_correct = (len(correct_indices) > 1)

    # if none are correct, we skip
    if not correct_indices:
        clear()
        print(f"[!] Pregunta {qid} sin respuestas correctas (tras advanced parse). Se omite...\n")
        # Mark performance as not unanswered
        if str(qid) not in perf_data:
            perf_data[str(qid)] = {}
        perf_data[str(qid)]["unanswered"] = False
        session_counts["correct"] += 1
        press_any_key()
        return True

    # show question
    clear()
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    # optional question text
    question_text = question_data["question"]
    source = question_data.get("_quiz_source","")
    if source:
        print(f"(Pregunta de: {os.path.basename(source)})\n")

    print(f"Pregunta {qid}:\n{question_text}\n")

    # print the final answers
    for i, adata in enumerate(answers_shuffled):
        new_label = chr(ord('A') + i)
        print(f"[{new_label}] {adata['display_text']}")

    print("\n[0] Salir de la sesión\n")
    if multi_correct:
        print("Puede haber varias respuestas correctas. Ej. 'A,C'")

    # user input
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

    # parse letters
    user_positions = []
    try:
        for p in opcion.split(","):
            p = p.strip()
            if p:
                idx = ord(p) - ord('A')
                user_positions.append(idx)
    except:
        user_positions = [-1]

    # check correctness
    if not multi_correct:
        if len(user_positions) == 1 and user_positions[0] in correct_indices:
            # correct
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
            # incorrect
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            session_counts["wrong"] += 1
            clear()
            print("¡INCORRECTO!\n")
            if wrongmsg:
                print(wrongmsg + "\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False
    else:
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
                print(wrongmsg + "\n")
            if explanation:
                print(f"EXPLICACIÓN:\n{explanation}\n")
            press_any_key()
            return False

def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    # We'll label them if needed
    for q in full_questions:
        label_original_answers(q)

    # build subset
    all_pairs = [(i, q) for i, q in enumerate(full_questions)]
    if file_filter:
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

    # optional shuffle subset to randomize question order
    # random.shuffle(subset)

    session_counts = {"correct":0,"wrong":0,"unanswered":0}
    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        result = preguntar(qid, qdata, perf_data, session_counts)
        if result is None:
            break
        save_performance_data(perf_data)
        idx += 1

    clear()
    print_local_summary(session_counts)

def comando_quiz_todos(questions, perf_data):
    play_quiz(questions, perf_data, "all", None)

def comando_quiz_sin_responder(questions, perf_data):
    play_quiz(questions, perf_data, "unanswered", None)

def comando_quiz_erroneos(questions, perf_data):
    play_quiz(questions, perf_data, "wrong", None)

def comando_reseteo(perf_data):
    confirm = input("¿Resetear progreso? (s/n) ").lower()
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
                print("[2] Solo no respondidas")
                print("[3] Solo erróneas")
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
    print(f"QuizProg v{VERSION} - Deep Parsing & Custom Logic\n")

    questions, cursos_dict, cursos_archivos = load_all_quizzes()
    print_cursos_summary(cursos_dict)

    perf_data = load_performance_data()

    while True:
        clear()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("1) Todas las preguntas (global)")
        print("2) Solo no respondidas (global)")
        print("3) Solo erróneas (global)")
        print("4) Elegir un curso y archivo específico")
        print("5) Resetear progreso")
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
