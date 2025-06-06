# quizlib/engine.py

import os
import re
import random
import copy
from datetime import date, datetime, time, timedelta

from .performance import save_performance_data
from .utils import clear_screen, press_any_key
from .loader import QUIZ_DATA_FOLDER

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ─── Chronometer ────────────────────────────────────────────────────────────────
class Chronometer:
    def __init__(self):
        self.elapsed = timedelta(0)
        self.running = False
        self._start = None

    def start(self):
        if not self.running:
            self._start = datetime.now()
            self.running = True

    def pause(self):
        if self.running:
            self.elapsed += datetime.now() - self._start
            self.running = False

    def get_elapsed(self):
        if self.running:
            return self.elapsed + (datetime.now() - self._start)
        return self.elapsed

    def formatted(self):
        total = int(self.get_elapsed().total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

# module‐level chrono, set in play_quiz()
chrono = None


def effective_today():
    """
    Return the 'current learning date', rolling over at 05:30 AM local time.
    If now < 05:30, treat it as the previous day.
    """
    now = datetime.now()
    cutoff = time(5, 30)
    today = date.today()
    if now.time() < cutoff:
        return today - timedelta(days=1)
    return today


def clean_embedded_answers(question_text):
    pattern = re.compile(r'^[a-dA-D]\)\s')
    lines = question_text.split('\n')
    return '\n'.join(line for line in lines if not pattern.match(line.strip())).strip()


def remap_answer_references(text, shuffle_mapping):
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
    Presenta una pregunta con SM-2 y estadísticas. Pausa el cronómetro
    durante la sección de explicación, luego lo reanuda.
    """
    global chrono
    # ensure timer is running while answering
    if chrono:
        chrono.start()

    qid_str = str(qid)
    if qid_str not in perf_data:
        perf_data[qid_str] = {"history": []}
    pd = perf_data[qid_str]

    # Initialize SM-2 fields if missing
    if "ease" not in pd:
        today = effective_today()
        pd.update({
            "ease": 2.5,
            "interval": 0,
            "repetition": 0,
            "next_review": today.isoformat()
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
    user_set = set()
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

    elif ui == "":
        # Skip
        pd["history"].append("skipped")
        session_counts["unanswered"] += 1
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

    # SM-2 scheduling...
    if quality >= 3:
        pd["repetition"] += 1
        if pd["repetition"] == 1:
            pd["interval"] = 1
        elif pd["repetition"] == 2:
            pd["interval"] = 3
        else:
            pd["interval"] = round(pd["interval"] * pd["ease"])
        pd["ease"] = max(
            1.3,
            pd["ease"] + (0.1 - (5-quality) * (0.08 + (5-quality) * 0.02))
        )
    else:
        pd["repetition"] = 0
        pd["interval"] = 1
        pd["ease"] = max(
            1.3,
            pd["ease"] + (0.1 - (5-quality) * (0.08 + (5-quality) * 0.02))
        )

    # Cap interval by exam_dates if provided...
    if exam_dates:
        source = question_data.get("_quiz_source", "")
        curso = None
        if isinstance(source, str):
            parts = os.path.normpath(source).split(os.sep)
            if len(parts) >= 2:
                curso = parts[-2]
        fecha_ex = exam_dates.get(curso)
        if fecha_ex:
            try:
                ex_date = date.fromisoformat(fecha_ex)
                today = effective_today()
                days_left = max((ex_date - today).days, 1)
                pd["interval"] = min(pd["interval"], days_left)
            except ValueError:
                pass

    # Compute next review date
    next_day = effective_today() + timedelta(days=pd["interval"])
    pd["next_review"] = next_day.isoformat()

    # Pause timer for explanation + history
    if chrono:
        chrono.pause()

    # Feedback + explanation
    clear_screen()
    print(colorize_answers(
        text, shuffled, shuffle_map,
        user_set,
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

    # Resume timer for next question
    if chrono:
        chrono.start()

    save_performance_data(perf_data)
    return quality == 5


def play_quiz(full_questions, perf_data, filter_mode="all",
              file_filter=None, tag_filter=None, exam_dates=None):
    """
    Ahora usa effective_today() para filtrar 'due' y cronometrar la sesión.
    """
    global chrono
    chrono = Chronometer()
    chrono.start()

    pairs = [(q.get("_quiz_id", idx), q) for idx, q in enumerate(full_questions)]

    pairs = []
    for idx, q in enumerate(full_questions):
        qid = q.get("_quiz_id", idx)
        pairs.append((qid, q))

    if file_filter:
        pairs = [(qid, q) for qid, q in pairs if q.get("_quiz_source") == file_filter]
    if tag_filter:
        pairs = [(qid, q) for qid, q in pairs if tag_filter in q.get("tags", [])]

    today = effective_today()
    if filter_mode == "due":
        subset = [
            (qid, q) for qid, q in pairs
            if not perf_data.get(str(qid), {}).get("next_review")
               or datetime.fromisoformat(perf_data[str(qid)]["next_review"]).date() <= today
        ]
    elif filter_mode == "unanswered":
        subset = [(qid, q) for qid, q in pairs if not perf_data.get(str(qid), {}).get("history")]
    elif filter_mode == "wrong":
        subset = [
            (qid, q) for qid, q in pairs
            if perf_data.get(str(qid), {}).get("history", []) and
               perf_data[str(qid)]["history"][-1] == "wrong"
        ]
    elif filter_mode == "wrong_unanswered":
        subset = [
            (qid, q) for qid, q in pairs
            if perf_data.get(str(qid), {}).get("history", []) and
               perf_data[str(qid)]["history"][-1] in ("wrong", "skipped")
        ]
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

    # show elapsed time
    print(f"Tiempo transcurrido: {chrono.formatted()}\n")
