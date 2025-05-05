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
    """Handler per Ctrl-C: esce ordinatamente."""
    clear_screen()
    print("\n¡Hasta luego!")
    sys.exit(0)

# Registriamo il handler non appena importiamo il modulo
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

def comando_quiz_todos(questions, perf_data):
    """Quiz con TUTTE le domande."""
    play_quiz(questions, perf_data, filter_mode="all", file_filter=None)

def comando_quiz_unanswered(questions, perf_data):
    """Quiz solo domande NON risposte."""
    play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=None)

def comando_quiz_wrong(questions, perf_data):
    """Quiz solo domande SBAGLIATE."""
    play_quiz(questions, perf_data, filter_mode="wrong", file_filter=None)

def comando_quiz_wrong_unanswered(questions, perf_data):
    """Quiz domande SBAGLIATE o NON risposte."""
    play_quiz(questions, perf_data, filter_mode="wrong_unanswered", file_filter=None)

def print_submenu_archivo():
    """
    Sub-menu dopo selezione file:
    permette di scegliere il filtro specifico per quell'archivio.
    """
    print("\n=== Filtro per il file selezionato ===")
    print("1) Realizar quiz con TODAS las preguntas (de este archivo)")
    print("2) Realizar quiz con preguntas NO respondidas (de este archivo)")
    print("3) Realizar quiz con preguntas FALLADAS (de este archivo)")
    print("4) Realizar quiz con preguntas FALLADAS o NO respondidas (de este archivo)")
    print("5) Volver al menú principal")

def comando_quiz_file(questions, perf_data, cursos_dict):
    chosen_filepath = pick_a_file_menu(cursos_dict)
    if not chosen_filepath:
        return
    while True:
        clear_screen()
        print_submenu_archivo()
        choice = input("\nSelecciona una opción: ").strip()
        if choice == "1":
            play_quiz(questions, perf_data, filter_mode="all", file_filter=chosen_filepath)
        elif choice == "2":
            play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=chosen_filepath)
        elif choice == "3":
            play_quiz(questions, perf_data, filter_mode="wrong", file_filter=chosen_filepath)
        elif choice == "4":
            play_quiz(questions, perf_data, filter_mode="wrong_unanswered", file_filter=chosen_filepath)
        elif choice == "5":
            break
        else:
            print("Opción no válida.")
            press_any_key()

def print_menu_principal():
    """Stampa il menu principale."""
    print("\n=== QuizProg Main Menu ===")
    print("1) Realizar quiz con TODAS las preguntas")
    print("2) Realizar quiz con preguntas NO respondidas")
    print("3) Realizar quiz con preguntas FALLADAS (anteriores)")
    print("4) Seleccionar un archivo específico y realizar su quiz")
    print("5) Ver resumen de archivos cargados")
    print("6) Realizar quiz con preguntas FALLADAS o NO respondidas")
    print("7) Ver estadísticas")
    print("8) Salir")

def comando_statistics(questions, perf_data, cursos_dict, quiz_files_info):
    """
    Mostra statistiche globali di domande: mai tentate, saltate, sbagliate, corrette.
    Permette di filtrare per libreria, corso (cartella) o file.
    """
    def compute_and_show(qids, label):
        never = skipped = wrong = correct = 0
        for qid in qids:
            hist = perf_data.get(str(qid), {}).get("history", [])
            if not hist:
                never += 1
            else:
                last = hist[-1]
                if last == "skipped":
                    skipped += 1
                elif last == "wrong":
                    wrong += 1
                elif last == "correct":
                    correct += 1
        total = len(qids)
        clear_screen()
        print(f"\n=== Estadísticas para {label} ===")
        print(f"Total preguntas: {total}")
        print(f"Sin intentar: {never}")
        print(f"Saltadas: {skipped}")
        print(f"Incorrectas: {wrong}")
        print(f"Correctas: {correct}\n")
        press_any_key()

    while True:
        clear_screen()
        print("\n=== Estadísticas ===")
        print("1) Librería completa")
        print("2) Carpeta (curso)")
        print("3) Archivo")
        print("4) Volver")
        choice = input("Selecciona una opción: ").strip()

        if choice == "1":
            qids = list(range(len(questions)))
            compute_and_show(qids, "Librería completa")

        elif choice == "2":
            course_names = sorted(cursos_dict.keys())
            while True:
                clear_screen()
                print("\n=== Cursos disponibles ===")
                for idx, cname in enumerate(course_names, start=1):
                    print(f"{idx}) {cname}")
                print("0) Volver")
                sel = input("Selecciona un curso: ").strip()
                if sel == "0":
                    break
                try:
                    ci = int(sel) - 1
                    if 0 <= ci < len(course_names):
                        chosen_course = course_names[ci]
                        qids = [
                            i for i, q in enumerate(questions)
                            if os.path.relpath(q.get("_quiz_source", ""),
                                               QUIZ_DATA_FOLDER
                            ).split(os.sep)[0] == chosen_course
                        ]
                        compute_and_show(qids, f"Curso '{chosen_course}'")
                        break
                except ValueError:
                    pass

        elif choice == "3":
            filepath = pick_a_file_menu(cursos_dict)
            if not filepath:
                continue
            qids = [
                i for i, q in enumerate(questions)
                if q.get("_quiz_source") == filepath
            ]
            compute_and_show(qids, f"Archivo '{os.path.basename(filepath)}'")

        elif choice == "4":
            return

        else:
            continue

def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s:%(name)s:%(message)s"
    )

    set_title(f"QuizProg v{VERSION}")

    clear_screen()
    print(f"QuizProg v{VERSION}")
    print(f"Usando carpeta de quizzes: '{QUIZ_DATA_FOLDER}'")
    press_any_key()

    questions, cursos_dict, quiz_files_info = load_all_quizzes(QUIZ_DATA_FOLDER)

    print("Archivos de Quiz Cargados")

    perf_data = load_performance_data()

    while True:
        clear_screen()
        print_menu_principal()
        choice = input("\nSelecciona una opción: ").strip()
        if choice == "1":
            comando_quiz_todos(questions, perf_data)
        elif choice == "2":
            comando_quiz_unanswered(questions, perf_data)
        elif choice == "3":
            comando_quiz_wrong(questions, perf_data)
        elif choice == "4":
            comando_quiz_file(questions, perf_data, cursos_dict)
        elif choice == "5":
            clear_screen()
            print_quiz_files_summary(quiz_files_info)
            press_any_key()
        elif choice == "6":
            comando_quiz_wrong_unanswered(questions, perf_data)
        elif choice == "7":
            comando_statistics(questions, perf_data, cursos_dict, quiz_files_info)
        elif choice == "8":
            clear_screen()
            print("¡Hasta luego!")
            sys.exit(0)
        else:
            print("Opción no válida.")
            press_any_key()

if __name__ == "__main__":
    main()
