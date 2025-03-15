# quizlib/engine.py

import os
import re
import random
import copy

from .performance import save_performance_data
from .utils import clear_screen, press_any_key

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def clean_embedded_answers(question_text):
    """
    Rimuove dal testo della domanda le linee che iniziano con 'a) ', 'b) ', ecc.
    per evitare di mostrare duplicazioni di opzioni in domande che contengono
    risposte incorporate.
    """
    pattern = re.compile(r'^[a-dA-D]\)\s')
    lines = question_text.split('\n')
    cleaned = []
    for line in lines:
        if pattern.match(line.strip()):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned).strip()

def remap_answer_references(text, shuffle_mapping):
    """
    Sostituisce i riferimenti letterali 'a', 'b', 'c', 'd' nel testo
    con le nuove lettere (A-D) post-shuffle, e cerca di ordinare eventuali riferimenti
    multipli (es: "B y A" => "A y B").
    """
    def replace_letter(m):
        old_letter = m.group(0).lower()
        old_idx = ord(old_letter) - ord('a')
        new_idx = shuffle_mapping.get(old_idx, old_idx)
        return LETTERS[new_idx]

    # 1) Sostituisce singole lettere a-d
    text = re.sub(r'\b[a-dA-D]\b', replace_letter, text)

    # 2) Riordina eventuali riferimenti multipli (es: "B y A" => "A y B")
    pattern = re.compile(r'\b([A-D])(\s+y\s+[A-D])+\b')
    while True:
        match = pattern.search(text)
        if not match:
            break
        full_match = match.group(0)
        letters_found = re.findall(r'[A-D]', full_match)
        sorted_letters = sorted(letters_found)
        new_phrase = ' y '.join(sorted_letters)
        if new_phrase == full_match:
            break
        text = text.replace(full_match, new_phrase, 1)

    return text

def colorize_answers(question_text, shuffled_answers, shuffle_mapping,
                     user_letters_set, correct_letters_set):
    """
    Ritorna la stringa con la domanda e le risposte colorate:
      - Risposta corretta in verde
      - Risposta sbagliata scelta dall'utente in rosso
      - Il resto in colore default
    """
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"

    lines = []
    lines.append(question_text)
    lines.append("")

    for idx, ans in enumerate(shuffled_answers):
        label = LETTERS[idx]
        ans_text = remap_answer_references(ans["text"], shuffle_mapping)

        if label in correct_letters_set:
            # verde
            color_code = GREEN
        elif label in user_letters_set:
            # rosso
            color_code = RED
        else:
            color_code = RESET

        lines.append(f"[{color_code}{label}{RESET}] {color_code}{ans_text}{RESET}")

    return "\n".join(lines)

def preguntar(qid, question_data, perf_data, session_counts, disable_shuffle=False):
    """
    Presenta una singola domanda, gestisce la risposta, aggiorna i contatori
    e i dati di performance. Ritorna:
      True => risposta corretta
      False => risposta errata
      None => l'utente ha scelto di uscire dalla sessione
    """
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear_screen()

    question_text = clean_embedded_answers(question_data["question"])
    original_answers = question_data["answers"]

    # Shuffle a meno che disable_shuffle sia True
    if not disable_shuffle:
        shuffled_answers = copy.deepcopy(original_answers)
        random.shuffle(shuffled_answers)
    else:
        shuffled_answers = original_answers[:]

    # Mappatura index originale -> index shuffle
    shuffle_mapping = {}
    for orig_idx, ans in enumerate(original_answers):
        new_idx = shuffled_answers.index(ans)
        shuffle_mapping[orig_idx] = new_idx

    print(f"Pregunta {qid}:\n{question_text}\n")

    # Stampiamo le risposte (senza colore in questa fase iniziale)
    for idx, ans in enumerate(shuffled_answers):
        ans_text = remap_answer_references(ans["text"], shuffle_mapping)
        label = LETTERS[idx]
        print(f"[{label}] {ans_text}")

    print("\n[0] Salir de la sesión\n")

    # Calcoliamo le lettere "corrette" nella nuova posizione
    correct_letters = []
    for orig_idx, ans in enumerate(original_answers):
        if ans.get("correct", False):
            new_idx = shuffle_mapping[orig_idx]
            correct_letters.append(LETTERS[new_idx])

    if len(correct_letters) > 1:
        print("Puede haber varias respuestas correctas. Ejemplo: 'A,C'")

    user_input = input("Tu respuesta: ").strip().upper()
    if user_input == "0":
        clear_screen()
        print("¿Seguro que deseas salir de esta sesión y volver al sub-menú? (s/n)")
        confirm = input("> ").strip().lower()
        if confirm == "s":
            session_counts["unanswered"] += 1
            return None
        # Se l'utente dice di NO, contiamola come sbagliata e passiamo oltre
        perf_data[str(qid)]["wrong"] = True
        session_counts["wrong"] += 1
        return False

    # Parsing multi-letter input
    delimiters_pattern = r'[,\s;]+'
    user_letters = re.split(delimiters_pattern, user_input)
    user_letters = [x.strip() for x in user_letters if x.strip()]
    user_letters_set = set(user_letters)
    correct_set = set(correct_letters)

    is_correct = (user_letters_set == correct_set and len(user_letters_set) == len(correct_letters))

    perf_data[str(qid)]["unanswered"] = False
    perf_data[str(qid)]["wrong"] = not is_correct

    if is_correct:
        session_counts["correct"] += 1
    else:
        session_counts["wrong"] += 1

    # Adesso rispulciamo la domanda con i colori
    clear_screen()
    colored_view = colorize_answers(question_text, shuffled_answers,
                                    shuffle_mapping, user_letters_set,
                                    correct_set)
    print(colored_view)
    print()

    if is_correct:
        print("¡CORRECTO!\n")
    else:
        print("¡INCORRECTO!\n")

    explanation = question_data.get("explanation", "")
    if explanation:
        explanation = remap_answer_references(explanation, shuffle_mapping)
        print(f"EXPLICACIÓN:\n{explanation}\n")

    press_any_key()
    return is_correct

def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    Esegue una sessione di quiz. Opzioni:
      - filter_mode: "all", "unanswered", "wrong"
      - file_filter: se non None, filtra le domande provenienti da un determinato file
    """
    # Costruiamo la lista con (indice, question_data)
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

    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}

    idx = 0
    total_q = len(subset)
    while idx < total_q:
        qid, qdata = subset[idx]
        result = preguntar(qid, qdata, perf_data, session_counts, disable_shuffle=False)
        save_performance_data(perf_data)
        if result is None:
            break
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
    if total > 0:
        score = (c * 0.333 - w * 0.111) / total * 30
        print(f'Punteggio: {score:.2f}/10 (sufficienza = 5)')
    press_any_key()
