# quizlib/main.py

import sys
import os
import logging
import signal

from quizlib.loader import load_all_quizzes, QUIZ_DATA_FOLDER
from quizlib.performance import load_performance_data
from quizlib.engine import play_quiz, clear_screen, press_any_key
from quizlib.navigator import pick_a_file_menu, print_quiz_files_summary

VERSION = "2.5.0"
logger = logging.getLogger(__name__)

def _sigint_handler(signum, frame):
    clear_screen()
    print("\n¡Hasta luego!")
    sys.exit(0)

signal.signal(signal.SIGINT, _sigint_handler)

def set_title(title):
    """Set the console title for Windows or via ANSI per altri OS."""
    if os.name == 'nt':
        import ctypes
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except:
            pass
    else:
        sys.stdout.write('\x1b]2;' + title + '\x07')

def comando_quiz_due(questions, perf_data, **kwargs):
    play_quiz(questions, perf_data, filter_mode="due", **kwargs)

def comando_quiz_todos(questions, perf_data, **kwargs):
    play_quiz(questions, perf_data, filter_mode="all", **kwargs)

def comando_quiz_unanswered(questions, perf_data, **kwargs):
    play_quiz(questions, perf_data, filter_mode="unanswered", **kwargs)

def comando_quiz_wrong(questions, perf_data, **kwargs):
    play_quiz(questions, perf_data, filter_mode="wrong", **kwargs)

def comando_quiz_wrong_unanswered(questions, perf_data, **kwargs):
    play_quiz(questions, perf_data, filter_mode="wrong_unanswered", **kwargs)

def comando_quiz_file(questions, perf_data, cursos_dict):
    fp = pick_a_file_menu(cursos_dict)
    if not fp:
        return
    while True:
        clear_screen()
        print("\n=== File Filter ===")
        print("1) Tutte")
        print("2) Non risposte")
        print("3) Sbagliate")
        print("4) Sbagliate o saltate")
        print("5) Programmato per oggi")
        print("6) Torna indietro")
        choice = input("Scelta: ").strip()
        if choice == "1":
            comando_quiz_todos(questions, perf_data, file_filter=fp)
        elif choice == "2":
            comando_quiz_unanswered(questions, perf_data, file_filter=fp)
        elif choice == "3":
            comando_quiz_wrong(questions, perf_data, file_filter=fp)
        elif choice == "4":
            comando_quiz_wrong_unanswered(questions, perf_data, file_filter=fp)
        elif choice == "5":
            comando_quiz_due(questions, perf_data, file_filter=fp)
        elif choice == "6":
            break

def comando_quiz_tag(questions, perf_data, tags_list):
    if not tags_list:
        clear_screen()
        print("[No tags available]")
        press_any_key()
        return
    while True:
        clear_screen()
        print("\n=== Tags disponibili ===")
        for i, t in enumerate(tags_list, 1):
            print(f"{i}) {t}")
        print("0) Torna indietro")
        sel = input("Seleziona tag: ").strip()
        if sel == "0":
            return
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(tags_list):
                comando_quiz_due(questions, perf_data, tag_filter=tags_list[idx])
                return
        except ValueError:
            pass

def comando_statistics(questions, perf_data, cursos_dict, quiz_files_info):
    def compute(qids, label):
        never = skipped = wrong = correct = 0
        for i in qids:
            h = perf_data.get(str(i), {}).get("history", [])
            if not h:
                never += 1
            else:
                last = h[-1]
                if last == "skipped":
                    skipped += 1
                elif last == "wrong":
                    wrong += 1
                elif last == "correct":
                    correct += 1
        total = len(qids)
        clear_screen()
        print(f"\n=== Statistiche {label} ===")
        print(f"Totale: {total}")
        print(f"Mai tentate: {never}")
        print(f"Saltate: {skipped}")
        print(f"Sbagliate: {wrong}")
        print(f"Corrette: {correct}\n")
        press_any_key()

    while True:
        clear_screen()
        print("\n=== Statistiche ===")
        print("1) Libreria completa")
        print("2) Corso (cartella)")
        print("3) File")
        print("4) Torna indietro")
        choice = input("Scelta: ").strip()
        if choice == "1":
            compute(list(range(len(questions))), "Libreria completa")
        elif choice == "2":
            courses = sorted(cursos_dict.keys())
            while True:
                clear_screen()
                print("\n=== Corsi ===")
                for i, c in enumerate(courses, 1):
                    print(f"{i}) {c}")
                print("0) Torna indietro")
                sel = input("Scelta: ").strip()
                if sel == "0":
                    break
                try:
                    ci = int(sel) - 1
                    if 0 <= ci < len(courses):
                        course = courses[ci]
                        qids = [
                            i for i, q in enumerate(questions)
                            if os.path.relpath(q["_quiz_source"], QUIZ_DATA_FOLDER)
                               .split(os.sep)[0] == course
                        ]
                        compute(qids, f"Corso {course}")
                        break
                except ValueError:
                    pass
        elif choice == "3":
            fp = pick_a_file_menu(cursos_dict)
            if not fp:
                continue
            qids = [i for i, q in enumerate(questions) if q["_quiz_source"] == fp]
            compute(qids, f"File {os.path.basename(fp)}")
        elif choice == "4":
            return

def print_menu():
    clear_screen()
    print(f"QuizProg v{VERSION}")
    print(f"Folder quiz: '{QUIZ_DATA_FOLDER}'\n")
    print("1) Ripasso programmato (oggi)")
    print("2) Tutte le domande")
    print("3) Non risposte")
    print("4) Sbagliate")
    print("5) Sbagliate o saltate")
    print("6) Per file")
    print("7) Per tag")
    print("8) Sommario file")
    print("9) Statistiche")
    print("0) Esci")

def main():
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s:%(name)s:%(message)s")
    set_title(f"QuizProg v{VERSION}")
    clear_screen()
    press_any_key()

    questions, cursos_dict, quiz_files_info = load_all_quizzes(QUIZ_DATA_FOLDER)
    perf_data = load_performance_data()
    # raccolta tags
    tags = sorted({t for q in questions for t in q.get("tags", [])})

    while True:
        print_menu()
        choice = input("Scelta: ").strip()
        if choice == "1":
            comando_quiz_due(questions, perf_data)
        elif choice == "2":
            comando_quiz_todos(questions, perf_data)
        elif choice == "3":
            comando_quiz_unanswered(questions, perf_data)
        elif choice == "4":
            comando_quiz_wrong(questions, perf_data)
        elif choice == "5":
            comando_quiz_wrong_unanswered(questions, perf_data)
        elif choice == "6":
            comando_quiz_file(questions, perf_data, cursos_dict)
        elif choice == "7":
            comando_quiz_tag(questions, perf_data, tags)
        elif choice == "8":
            clear_screen()
            print_quiz_files_summary(quiz_files_info)
            press_any_key()
        elif choice == "9":
            comando_statistics(questions, perf_data, cursos_dict, quiz_files_info)
        elif choice == "0":
            clear_screen()
            print("¡Hasta luego!")
            sys.exit(0)
        else:
            continue

if __name__ == "__main__":
    main()
