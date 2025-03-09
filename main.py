# main.py

import sys
import os
from quizlib.loader import load_all_quizzes, QUIZ_DATA_FOLDER
from quizlib.performance import load_performance_data, save_performance_data
from quizlib.engine import play_quiz, clear_screen, press_any_key
from quizlib.navigator import pick_a_file_menu, get_file_question_count

VERSION = "2.4.1"

def comando_quiz_todos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="all", file_filter=None)

def comando_quiz_sin_responder(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=None)

def comando_quiz_erroneos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="wrong", file_filter=None)

def comando_elegir_archivo(questions, perf_data, cursos_dict):
    """Let the user navigate courses → sections → files, then quiz on that single file."""
    selected_filepath = pick_a_file_menu(cursos_dict)
    if not selected_filepath:
        # User canceled or no valid choice
        return

    # Count how many questions are in that file.
    question_count = get_file_question_count(questions, selected_filepath)
    filename = os.path.basename(selected_filepath)
    print(f"\nHas elegido el archivo '{filename}' con {question_count} preguntas.\n")
    press_any_key()

    # Now run the quiz for that single file.
    play_quiz(questions, perf_data, filter_mode="all", file_filter=selected_filepath)

def comando_salir():
    print("¡Hasta luego!")
    sys.exit(0)

def main():
    clear_screen()
    print(f"QuizProg v{VERSION}")

    # 1) Load all quiz data.
    questions, cursos_dict, quiz_files_info = load_all_quizzes(QUIZ_DATA_FOLDER)

    # 2) Load performance data.
    perf_data = load_performance_data()

    while True:
        clear_screen()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("1) Todas las preguntas (global)")
        print("2) Solo preguntas no respondidas (global)")
        print("3) Solo preguntas erróneas (global)")
        print("4) Elegir un archivo específico")
        print("5) Salir\n")

        choice = input("Selecciona una opción: ").strip()
        if choice == "1":
            comando_quiz_todos(questions, perf_data)
        elif choice == "2":
            comando_quiz_sin_responder(questions, perf_data)
        elif choice == "3":
            comando_quiz_erroneos(questions, perf_data)
        elif choice == "4":
            comando_elegir_archivo(questions, perf_data, cursos_dict)
        elif choice == "5":
            comando_salir()
        else:
            pass

if __name__ == "__main__":
    main()
