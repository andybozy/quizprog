# quizprog/main.py

import sys
from quizlib.loader import load_all_quizzes, QUIZ_DATA_FOLDER
from quizlib.performance import load_performance_data, save_performance_data
from quizlib.engine import play_quiz, clear_screen, press_any_key

VERSION = "2.4.1"

def comando_quiz_todos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="all", file_filter=None)

def comando_quiz_sin_responder(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=None)

def comando_quiz_erroneos(questions, perf_data):
    play_quiz(questions, perf_data, filter_mode="wrong", file_filter=None)

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

def main():
    clear_screen()
    print(f"QuizProg v{VERSION}")

    # Load quizzes -> now returning (questions, cursos_dict, quiz_files_info)
    questions, cursos_dict, quiz_files_info = load_all_quizzes(QUIZ_DATA_FOLDER)

    perf_data = load_performance_data()

    while True:
        clear_screen()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print("1) Todas las preguntas (global)")
        print("2) Solo preguntas no respondidas (global)")
        print("3) Solo preguntas erróneas (global)")
        print("4) Salir\n")

        choice = input("Selecciona una opción: ").strip()
        if choice == "1":
            comando_quiz_todos(questions, perf_data)
        elif choice == "2":
            comando_quiz_sin_responder(questions, perf_data)
        elif choice == "3":
            comando_quiz_erroneos(questions, perf_data)
        elif choice == "4":
            comando_salir()
        else:
            pass

if __name__ == "__main__":
    main()
