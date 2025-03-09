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
    Remove lines starting with something like 'a) ' or 'b) ' (case-insensitive)
    to avoid showing embedded letter-labeled lines in the question text.
    """
    lines = question_text.split('\n')
    cleaned = []
    pattern = re.compile(r'^[a-dA-D]\)\s')
    for line in lines:
        if pattern.match(line.strip()):
            # skip lines like "a) text", "b) text", etc.
            continue
        cleaned.append(line)
    return '\n'.join(cleaned).strip()

def remap_answer_references(text, shuffle_mapping):
    """
    Replaces original letter references (like 'a', 'b', etc.) with the new letters
    after shuffling.

    For instance, if the text references 'a' or 'c', we might change them to 'B' or 'A'
    according to the shuffle mapping.

    Also sorts multi references so that "B y A" => "A y B".
    """

    def replace_letter(m):
        old_letter = m.group(0).lower()
        old_idx = ord(old_letter) - ord('a')
        new_idx = shuffle_mapping.get(old_idx, old_idx)
        return LETTERS[new_idx]

    # 1) Replace single letters a-d in the text with new letters from shuffle_mapping
    text = re.sub(r'\b[a-dA-D]\b', replace_letter, text)

    # 2) Now fix any multiple references like "B y A" => "A y B"
    pattern = re.compile(r'\b([A-D])(\s+y\s+[A-D])+\b')
    while True:
        match = pattern.search(text)
        if not match:
            break
        full_match = match.group(0)
        letters_found = re.findall(r'[A-D]', full_match)
        sorted_letters = sorted(letters_found)
        new_phrase = ' y '.join(sorted_letters)

        # Prevent infinite loop if nothing changes
        if new_phrase == full_match:
            break

        text = text.replace(full_match, new_phrase, 1)

    return text

def preguntar(qid, question_data, perf_data, session_counts, disable_shuffle=False):
    """
    Present one question. Returns:
      True => user answered correctly
      False => user answered incorrectly
      None => user decided to exit session

    :param disable_shuffle: If True, do not randomize the answer order.
                           Useful for stable ordering in tests.
    """
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}

    clear_screen()

    # Clean up embedded lines in the question, but do NOT remap letters in the question text
    question_text = clean_embedded_answers(question_data["question"])
    original_answers = question_data["answers"]

    # Shuffle answers unless disabled
    if not disable_shuffle:
        shuffled_answers = copy.deepcopy(original_answers)
        random.shuffle(shuffled_answers)
    else:
        shuffled_answers = original_answers[:]

    # Build mapping: original_idx -> new_idx
    shuffle_mapping = {}
    for orig_idx, ans in enumerate(original_answers):
        new_idx = shuffled_answers.index(ans)
        shuffle_mapping[orig_idx] = new_idx

    print(f"Pregunta {qid}:\n{question_text}\n")

    # Print each answer with new letter labeling (remapping references if needed)
    for idx, ans in enumerate(shuffled_answers):
        ans_text = remap_answer_references(ans["text"], shuffle_mapping)
        label = LETTERS[idx]
        print(f"[{label}] {ans_text}")

    print("\n[0] Salir de la sesión\n")

    # Determine the correct letters in the new shuffled positions
    correct_letters = []
    for orig_idx, ans in enumerate(original_answers):
        if ans.get("correct", False):
            new_idx = shuffle_mapping[orig_idx]
            correct_letters.append(LETTERS[new_idx])

    # If multiple correct, mention it
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
        # Otherwise let them re-answer once
        perf_data[str(qid)]["wrong"] = True
        session_counts["wrong"] += 1
        return False

    # Accept various delimiters for multiple answers: spaces, commas, semicolons
    delimiters_pattern = r'[,\s;]+'
    user_letters = [x.strip() for x in re.split(delimiters_pattern, user_input) if x.strip()]
    user_letters_set = set(user_letters)
    correct_set = set(correct_letters)

    # Check correctness
    if user_letters_set == correct_set and len(user_letters_set) == len(correct_letters):
        perf_data[str(qid)]["unanswered"] = False
        perf_data[str(qid)]["wrong"] = False
        session_counts["correct"] += 1

        clear_screen()
        print("¡CORRECTO!\n")

        # Remap explanation if present
        explanation = question_data.get("explanation", "")
        if explanation:
            explanation = remap_answer_references(explanation, shuffle_mapping)
            print(f"EXPLICACIÓN:\n{explanation}\n")

        press_any_key()
        return True
    else:
        perf_data[str(qid)]["unanswered"] = False
        perf_data[str(qid)]["wrong"] = True
        session_counts["wrong"] += 1

        clear_screen()
        print("¡INCORRECTO!\n")

        # Also remap explanation for consistency
        explanation = question_data.get("explanation", "")
        if explanation:
            explanation = remap_answer_references(explanation, shuffle_mapping)
            print(f"EXPLICACIÓN:\n{explanation}\n")

        press_any_key()
        return False

def play_quiz(full_questions, perf_data, filter_mode="all", file_filter=None):
    """
    Run a quiz session. Options:
      - filter_mode: "all", "unanswered", "wrong"
      - file_filter: if provided, only quiz questions from that file
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
        print("\n[No hay preguntas para este filtro. Volviendo...]\n")
        press_any_key()
        return

    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}

    idx = 0
    while idx < len(subset):
        qid, qdata = subset[idx]
        result = preguntar(qid, qdata, perf_data, session_counts, disable_shuffle=False)
        save_performance_data(perf_data)

        if result is None:
            # user wants to exit early
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
    press_any_key()
