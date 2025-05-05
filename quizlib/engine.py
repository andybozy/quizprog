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
        letters = sorted(re.findall(r'[A-D]', match.group(0)))
        text = text.replace(match.group(0), ' y '.join(letters), 1)
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
              disable_shuffle=False, exam_dates=None):
    """
    Presenta una pregunta, aggiorna SM-2 con cap basato sulla data d'esame del corso,
    e mostra statistiche in spagnolo.
    """
    qid_str = str(qid)
    if qid_str not in perf_data:
        perf_data[qid_str] = {"history": []}
    pd = perf_data[qid_str]

    # Inizializza campi SM-2
    if "ease" not in pd:
        pd.update({
            "ease": 2.5,
            "interval": 0,
            "repetition": 0,
            "next_review": date.today().isoformat()
        })

    clear_screen()
    question_text = clean_embedded_answers(question_data["question"])
    original_answers = question_data["answers"]

    # shuffle se non disabilitato
    if not disable_shuffle:
        shuffled_answers = copy.deepcopy(original_answers)
        random.shuffle(shuffled_answers)
    else:
        shuffled_answers = original_answers[:]

    shuffle_mapping = {i: shuffled_answers.index(ans)
                       for i, ans in enumerate(original_answers)}

    # Mostra domanda e risposte
    print(f"Pregunta {qid}:\n{question_text}\n")
    for idx, ans in enumerate(shuffled_answers):
        print(f"[{LETTERS[idx]}] {remap_answer_references(ans['text'], shuffle_mapping)}")
    print("\n[0] Salir\n")

    # Trova risposte corrette
    correct_letters = [
        LETTERS[shuffle_mapping[i]]
        for i, ans in enumerate(original_answers) if ans.get("correct", False)
    ]
    if len(correct_letters) > 1:
        print("Puede haber varias respuestas correctas, p.ej. 'A,C'")

    user_input = input("Tu respuesta: ").strip().upper()
    if user_input == "0":
        clear_screen()
        print("¿Confirmas salir? (s/n)")
        if input("> ").strip().lower() == "s":
            pd["history"].append("skipped")
            session_counts["unanswered"] += 1
            quality = 0
        else:
            pd["history"].append("wrong")
            session_counts["wrong"] += 1
            quality = 0
    else:
        parts = re.split(r'[,\s;]+', user_input)
        user_set = set(filter(None, parts))
        correct_set = set(correct_letters)
        is_correct = user_set == correct_set and len(user_set) == len(correct_letters)
        pd["history"].append("correct" if is_correct else "wrong")
        session_counts["correct" if is_correct else "wrong"] += 1
        quality = 5 if is_correct else 0

    # SM-2: calcola nuovo interval e ease
    if quality >= 3:
        pd["repetition"] += 1
        if pd["repetition"] == 1:
            pd["interval"] = 1
        elif pd["repetition"] == 2:
            pd["interval"] = 3   # tarato per esami a breve termine
        else:
            pd["interval"] = round(pd["interval"] * pd["ease"])
        pd["ease"] = max(1.3, pd["ease"] + (0.1 - (5-quality)*(0.08+(5-quality)*0.02)))
    else:
        pd["repetition"] = 0
        pd["interval"] = 1
        pd["ease"] = max(1.3, pd["ease"] + (0.1 - (5-quality)*(0.08+(5-quality)*0.02)))

    # Cap dell'intervallo in base all'esame del corso
    if exam_dates:
        source = question_data.get("_quiz_source", "")
        rel = os.path.relpath(source, QUIZ_DATA_FOLDER)
        curso = rel.split(os.sep)[0] if rel else None
        fecha_ex = exam_dates.get(curso)
        if fecha_ex:
            try:
                exam_date = date.fromisoformat(fecha_ex)
                dias_restantes = (exam_date - date.today()).days
                if dias_restantes < 1:
                    dias_restantes = 1
                pd["interval"] = min(pd["interval"], dias_restantes)
            except ValueError:
                pass

    pd["next_review"] = (date.today() + timedelta(days=pd["interval"])).isoformat()

    # Mostra feedback e statistiche
    clear_screen()
    print(colorize_answers(
        question_text, shuffled_answers, shuffle_mapping,
        set(re.split(r'[,\s;]+', user_input)) if user_input != "0" else set(),
        set(correct_letters)
    ))
    print("\n¡CORRECTO!\n" if quality == 5 else "\n¡INCORRECTO!\n")
    if question_data.get("explanation"):
        print("EXPLICACIÓN:\n" +
              remap_answer_references(question_data["explanation"], shuffle_mapping) + "\n")

    h = pd["history"]
    print(f"Historial: intentos={len(h)}, correctas={h.count('correct')}, "
          f"incorrectas={h.count('wrong')}, saltadas={h.count('skipped')}\n")
    press_any_key()
    save_performance_data(perf_data)
    return quality == 5

def play_quiz(full_questions, perf_data, filter_mode="all",
              file_filter=None, tag_filter=None, exam_dates=None):
    """
    filter_mode:
      - "due": programadas para hoy
      - "all": todas
      - "unanswered": no respondidas
      - "wrong": falladas última vez
      - "wrong_unanswered": falladas o saltadas
    Siempre prioriza cap SM-2 con date examen por curso.
    """
    pairs = [(i, q) for i, q in enumerate(full_questions)]
    if file_filter:
        pairs = [(i, q) for i, q in pairs if q.get("_quiz_source") == file_filter]
    if tag_filter:
        pairs = [(i, q) for i, q in pairs if tag_filter in q.get("tags", [])]

    today = date.today()
    if filter_mode == "due":
        subset = []
        for i, q in pairs:
            nr = perf_data.get(str(i), {}).get("next_review")
            if not nr or datetime.fromisoformat(nr).date() <= today:
                subset.append((i, q))
    elif filter_mode == "unanswered":
        subset = [(i, q) for i, q in pairs if not perf_data.get(str(i), {}).get("history")]
    elif filter_mode == "wrong":
        subset = [(i, q) for i, q in pairs
                  if perf_data.get(str(i), {}).get("history", [])[-1] == "wrong"]
    elif filter_mode == "wrong_unanswered":
        subset = [(i, q) for i, q in pairs
                  if perf_data.get(str(i), {}).get("history", [])[-1] in ("wrong", "skipped")]
        subset.sort(key=lambda x: perf_data[str(x[0])]["history"].count("wrong"), reverse=True)
    else:
        subset = pairs

    if not subset:
        clear_screen()
        print("\n[No hay preguntas para este filtro]\n")
        press_any_key()
        return

    counts = {"correct": 0, "wrong": 0, "unanswered": 0}
    for qid, qdata in subset:
        res = preguntar(qid, qdata, perf_data, counts,
                        disable_shuffle=False, exam_dates=exam_dates)
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
    press_any_key()
