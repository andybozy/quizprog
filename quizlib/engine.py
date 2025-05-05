# quizlib/engine.py

import os
import re
import random
import copy
from datetime import date, datetime, timedelta

from .performance import save_performance_data
from .utils import clear_screen, press_any_key
from .loader import QUIZ_DATA_FOLDER

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def clean_embedded_answers(question_text):
    pattern = re.compile(r'^[a-dA-D]\)\s')
    lines = question_text.split('\n')
    return '\n'.join(line for line in lines if not pattern.match(line.strip())).strip()


def remap_answer_references(text, shuffle_mapping):
    """
    Rimpiazza le lettere a-d con le nuove lettere (A-D) secondo shuffle_mapping,
    e ordina frasi multiple tipo "B y A y C" -> "A y B y C", evitando loop infiniti.
    """
    def replace_letter(m):
        old_idx = ord(m.group(0).lower()) - ord('a')
        new_idx = shuffle_mapping.get(old_idx, old_idx)
        return LETTERS[new_idx]

    text = re.sub(r'\b[a-dA-D]\b', replace_letter, text)
    pattern = re.compile(r'\b([A-D])(\s+y\s+[A-D])+\b')
    while True:
        match = pattern.search(text)
        if not match:
            break
        full = match.group(0)
        letters = re.findall(r'[A-D]', full)
        sorted_letters = sorted(letters)
        new_phrase = ' y '.join(sorted_letters)
        if new_phrase == full:
            break
        text = text.replace(full, new_phrase, 1)
    return text


def colorize_answers(question_text, shuffled_answers, shuffle_mapping,
                     user_letters_set, correct_letters_set):
    GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"
    lines = [question_text, ""]
    for idx, ans in enumerate(shuffled_answers):
        label = LETTERS[idx]
        ans_text = remap_answer_references(ans["text"], shuffle_mapping)
        if label in correct_letters_set:
            color = GREEN
        elif label in user_letters_set:
            color = RED
        else:
            color = RESET
        lines.append(f"[{color}{label}{RESET}] {color}{ans_text}{RESET}")
    return "\n".join(lines)


def preguntar(qid, question_data, perf_data, session_counts,
              disable_shuffle=False, exam_dates=None,
              position=None, total=None):
    """
    Presenta una pregunta con avanzamento, SM-2 tarato y estadísticas en español.
    Ahora usa 'qid' como clave de performance_data.
    """
    qid_str = str(qid)
    if qid_str not in perf_data:
        perf_data[qid_str] = {"history": []}
    pd = perf_data[qid_str]

    # Initialize SM-2 fields if missing
    if "ease" not in pd:
        pd.update({
            "ease": 2.5,
            "interval": 0,
            "repetition": 0,
            "next_review": date.today().isoformat()
        })

    clear_screen()
    text = clean_embedded_answers(question_data["question"])
    orig = question_data["answers"]

    # Header with progress
    if position is not None and total is not None:
        print(f"Pregunta {qid}   {position}/{total}\n{text}\n")
    else:
        print(f"Pregunta {qid}:\n{text}\n")

    # Shuffle answers
    if not disable_shuffle:
        shuffled = copy.deepcopy(orig)
        random.shuffle(shuffled)
    else:
        shuffled = orig[:]

    shuffle_map = {i: shuffled.index(ans) for i, ans in enumerate(orig)}

    for idx, ans in enumerate(shuffled):
        print(f"[{LETTERS[idx]}] {remap_answer_references(ans['text'], shuffle_map)}")
    print("\n[0] Salir\n")

    correct_letters = [
        LETTERS[shuffle_map[i]]
        for i, ans in enumerate(orig) if ans.get("correct", False)
    ]
    if len(correct_letters) > 1:
        print("Puede haber varias respuestas correctas, p.ej. 'A,C'")

    # User input
    ui = input("Tu respuesta: ").strip().upper()
    if ui == "0":
        clear_screen()
        print("¿Confirmas salir? (s/n)")
        conf = input("> ").strip().lower()
        if conf == "s":
            pd["history"].append("skipped")
            session_counts["unanswered"] += 1
            save_performance_data(perf_data)
            return None
        else:
            pd["history"].append("wrong")
            session_counts["wrong"] += 1
            quality = 0
    else:
        parts = re.split(r'[,\s;]+', ui)
        user_set = set(filter(None, parts))
        correct_set = set(correct_letters)
        is_correct = user_set == correct_set and len(user_set) == len(correct_letters)
        pd["history"].append("correct" if is_correct else "wrong")
        if is_correct:
            session_counts["correct"] += 1
            quality = 5
        else:
            session_counts["wrong"] += 1
            quality = 0

    # SM-2 scheduling
    if quality >= 3:
        pd["repetition"] += 1
        if pd["repetition"] == 1:
            pd["interval"] = 1
        elif pd["repetition"] == 2:
            pd["interval"] = 3
        else:
            pd["interval"] = round(pd["interval"] * pd["ease"])
        pd["ease"] = max(1.3, pd["ease"] + (0.1 - (5-quality)*(0.08+(5-quality)*0.02)))
    else:
        pd["repetition"] = 0
        pd["interval"] = 1
        pd["ease"] = max(1.3, pd["ease"] + (0.1 - (5-quality)*(0.08+(5-quality)*0.02)))

    # Cap interval by exam_dates if provided
    if exam_dates:
        source = question_data.get("_quiz_source", "")
        rel = os.path.relpath(source, QUIZ_DATA_FOLDER)
        curso = rel.split(os.sep)[0] if rel else None
        fecha_ex = exam_dates.get(curso)
        if fecha_ex:
            try:
                ex_date = date.fromisoformat(fecha_ex)
                days_left = (ex_date - date.today()).days
                days_left = max(days_left, 1)
                pd["interval"] = min(pd["interval"], days_left)
            except ValueError:
                pass

    pd["next_review"] = (date.today() + timedelta(days=pd["interval"])).isoformat()

    # Feedback
    clear_screen()
    print(colorize_answers(
        text, shuffled, shuffle_map,
        set(user_set) if ui != "0" else set(),
        set(correct_letters)
    ))
    print("\n¡CORRECTO!\n" if quality == 5 else "\n¡INCORRECTO!\n")
    if question_data.get("explanation"):
        expl = remap_answer_references(question_data["explanation"], shuffle_map)
        print("EXPLICACIÓN:\n" + expl + "\n")

    hist = pd["history"]
    print(f"Historial: intentos={len(hist)}, correctas={hist.count('correct')}, "
          f"incorrectas={hist.count('wrong')}, saltadas={hist.count('skipped')}\n")

    press_any_key()
    save_performance_data(perf_data)
    return quality == 5


def play_quiz(full_questions, perf_data, filter_mode="all",
              file_filter=None, tag_filter=None, exam_dates=None):
    """
    Now pairs = [(qid, question_dict), …] keyed by:
     - the question’s `_quiz_id` (if present), or
     - its list‐index (for old‐style tests/code).
    """
    pairs = []
    for idx, q in enumerate(full_questions):
        # fallback to index if loader didn't inject a _quiz_id
        qid = q.get("_quiz_id", idx)
        pairs.append((qid, q))

    if file_filter:
        pairs = [(qid, q) for qid, q in pairs if q.get("_quiz_source") == file_filter]
    if tag_filter:
        pairs = [(qid, q) for qid, q in pairs if tag_filter in q.get("tags", [])]

    today = date.today()
    if filter_mode == "due":
        subset = [
            (qid, q) for qid, q in pairs
            if not perf_data.get(str(qid), {}).get("next_review")
               or datetime.fromisoformat(perf_data[str(qid)]["next_review"]).date() <= today
        ]
    elif filter_mode == "unanswered":
        subset = [(qid, q) for qid, q in pairs if not perf_data.get(str(qid), {}).get("history")]
    elif filter_mode == "wrong":
        subset = [(qid, q) for qid, q in pairs
                  if perf_data.get(str(qid), {}).get("history", [])[-1] == "wrong"]
    elif filter_mode == "wrong_unanswered":
        subset = [(qid, q) for qid, q in pairs
                  if perf_data.get(str(qid), {}).get("history", [])[-1] in ("wrong", "skipped")]
        subset.sort(
            key=lambda x: perf_data[str(x[0])]["history"].count("wrong"),
            reverse=True
        )
    else:
        subset = pairs

    if not subset:
        clear_screen()
        print("\n[No hay preguntas para este filtro]\n")
        press_any_key()
        return

    counts = {"correct": 0, "wrong": 0, "unanswered": 0}
    total_q = len(subset)
    for position, (qid, qdata) in enumerate(subset, start=1):
        res = preguntar(
            qid, qdata, perf_data, counts,
            disable_shuffle=False,
            exam_dates=exam_dates,
            position=position,
            total=total_q
        )
        if res is None:
            break

    clear_screen()
    c, w, u = counts["correct"], counts["wrong"], counts["unanswered"]
    total = c + w + u
    print("=== Resumen de sesión ===")
    print(f"Correctas: {c}, Incorrectas: {w}, Saltadas: {u}, Total: {total}")
    if total:
        score = (c*0.333 - w*0.111)/total*30
        print(f"Puntuación: {score:.2f}/10\n")
    # (no final press_any_key to keep tests non-blocking)
