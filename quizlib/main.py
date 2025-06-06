# quizlib/main.py

import sys
import os
import logging
import signal
import json
from datetime import datetime

from quizlib.loader import load_all_quizzes, QUIZ_DATA_FOLDER
from quizlib.performance import load_performance_data
from quizlib.engine import (
    play_quiz,
    clear_screen,
    press_any_key,
    effective_today,
)
from quizlib.navigator import pick_a_file_menu

VERSION = "2.7.0"
logger = logging.getLogger(__name__)


def _sigint_handler(signum, frame):
    clear_screen()
    print("\n¡Hasta luego!")
    sys.exit(0)


signal.signal(signal.SIGINT, _sigint_handler)


def set_title(title):
    """Set the console title for Windows or via ANSI on other OS."""
    if os.name == 'nt':
        import ctypes
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except:
            pass
    else:
        sys.stdout.write('\x1b]2;' + title + '\x07')


def cargar_fechas_examen():
    exam_dates = {}
    fichero = os.path.join(QUIZ_DATA_FOLDER, "exam_dates.json")
    if os.path.exists(fichero):
        try:
            with open(fichero, encoding="utf-8") as f:
                exam_dates = json.load(f)
        except:
            pass
    return exam_dates


def comando_resumen_archivos(questions, perf_data, cursos_dict, quiz_files_info):
    while True:
        clear_screen()
        print("=== Resumen de Archivos ===\n")

        today = effective_today()

        # 1) Overall per-file summary
        for idx, finfo in enumerate(quiz_files_info, start=1):
            filepath = finfo["filepath"]
            filename = finfo["filename"]
            qids = [q["_quiz_id"] for q in questions if q["_quiz_source"] == filepath]
            total = len(qids)

            never = skipped = wrong = correct = due = 0

            for qid in qids:
                entry = perf_data.get(str(qid), {})
                history = entry.get("history", [])
                if not history:
                    never += 1
                else:
                    last = history[-1]
                    if last == "skipped":
                        skipped += 1
                    elif last == "wrong":
                        wrong += 1
                    elif last == "correct":
                        correct += 1

                nr = entry.get("next_review")
                if not nr or datetime.fromisoformat(nr).date() <= today:
                    due += 1

            def pct(x): return f"{(x/total*100):.1f}%" if total else "N/A"

            print(
                f"{idx}) {filename}: total={total}, "
                f"no-int={never} ({pct(never)}), saltadas={skipped} ({pct(skipped)}), "
                f"wrong={wrong} ({pct(wrong)}), correct={correct} ({pct(correct)}), "
                f"programadas={due} ({pct(due)})"
            )

        print("\n---\n")

        # 2) Per-course summary
        print("=== Resumen de Cursos ===\n")
        for curso, data in cursos_dict.items():
            total = data["total_questions"]
            never = skipped = wrong = correct = due = 0

            for q in questions:
                rel = os.path.relpath(q["_quiz_source"], QUIZ_DATA_FOLDER)
                if rel.split(os.sep)[0] != curso:
                    continue
                qid = q["_quiz_id"]
                entry = perf_data.get(str(qid), {})
                history = entry.get("history", [])

                if not history:
                    never += 1
                else:
                    last = history[-1]
                    if last == "skipped":
                        skipped += 1
                    elif last == "wrong":
                        wrong += 1
                    elif last == "correct":
                        correct += 1

                nr = entry.get("next_review")
                if not nr or datetime.fromisoformat(nr).date() <= today:
                    due += 1

            def pct2(x): return f"{(x/total*100):.1f}%" if total else "N/A"

            print(
                f"{curso}: total={total}, "
                f"no-int={never} ({pct2(never)}), saltadas={skipped} ({pct2(skipped)}), "
                f"wrong={wrong} ({pct2(wrong)}), correct={correct} ({pct2(correct)}), "
                f"programadas={due} ({pct2(due)})"
            )

        print("\n---\n")
        print("0) Volver")
        print("Seleccione un archivo (número) para ver sus estadísticas individuales, o 0 para volver.")

        choice = input("Elige opción: ").strip()
        if choice == "0":
            break

        try:
            sel = int(choice) - 1
            if 0 <= sel < len(quiz_files_info):
                finfo = quiz_files_info[sel]
                filepath = finfo["filepath"]
                filename = finfo["filename"]
                qids = [q["_quiz_id"] for q in questions if q["_quiz_source"] == filepath]
                total = len(qids)
                never = skipped = wrong = correct = due = 0

                for qid in qids:
                    entry = perf_data.get(str(qid), {})
                    history = entry.get("history", [])
                    if not history:
                        never += 1
                    else:
                        last = history[-1]
                        if last == "skipped":
                            skipped += 1
                        elif last == "wrong":
                            wrong += 1
                        elif last == "correct":
                            correct += 1

                    nr = entry.get("next_review")
                    if not nr or datetime.fromisoformat(nr).date() <= today:
                        due += 1

                def pct3(x): return f"{(x/total*100):.1f}%" if total else "N/A"

                clear_screen()
                print(f"=== Estadísticas detalladas: {filename} ===\n")
                print(f"Total preguntas         : {total}")
                print(f"Sin intentar            : {never} ({pct3(never)})")
                print(f"Saltadas                : {skipped} ({pct3(skipped)})")
                print(f"Incorrectas             : {wrong} ({pct3(wrong)})")
                print(f"Correctas               : {correct} ({pct3(correct)})")
                print(f"Programadas para hoy    : {due} ({pct3(due)})\n")
                press_any_key()
        except ValueError:
            continue


def comando_quiz_programado(questions, perf_data, exam_dates, **kwargs):
    play_quiz(questions, perf_data, filter_mode="due", exam_dates=exam_dates, **kwargs)


def comando_quiz_todas(questions, perf_data, exam_dates, **kwargs):
    play_quiz(questions, perf_data, filter_mode="all", exam_dates=exam_dates, **kwargs)


def comando_quiz_no_respondidas(questions, perf_data, exam_dates, **kwargs):
    play_quiz(questions, perf_data, filter_mode="unanswered", exam_dates=exam_dates, **kwargs)


def comando_quiz_falladas(questions, perf_data, exam_dates, **kwargs):
    play_quiz(questions, perf_data, filter_mode="wrong", exam_dates=exam_dates, **kwargs)


def comando_quiz_falladas_o_saltadas(questions, perf_data, exam_dates, **kwargs):
    play_quiz(questions, perf_data, filter_mode="wrong_unanswered", exam_dates=exam_dates, **kwargs)


def comando_quiz_por_archivo(questions, perf_data, cursos_dict, exam_dates):
    fichero = pick_a_file_menu(cursos_dict)
    if not fichero:
        return
    while True:
        clear_screen()
        print("\n=== Selección de archivo ===")
        print("1) Todas")
        print("2) No respondidas")
        print("3) Falladas")
        print("4) Falladas o saltadas")
        print("5) Programadas para hoy")
        print("6) Volver")
        elec = input("Elige opción: ").strip()
        if elec == "1":
            comando_quiz_todas(questions, perf_data, exam_dates, file_filter=fichero)
        elif elec == "2":
            comando_quiz_no_respondidas(questions, perf_data, exam_dates, file_filter=fichero)
        elif elec == "3":
            comando_quiz_falladas(questions, perf_data, exam_dates, file_filter=fichero)
        elif elec == "4":
            comando_quiz_falladas_o_saltadas(questions, perf_data, exam_dates, file_filter=fichero)
        elif elec == "5":
            comando_quiz_programado(questions, perf_data, exam_dates, file_filter=fichero)
        elif elec == "6":
            break
        else:
            print("Opción no válida.")
            press_any_key()


def comando_quiz_por_etiqueta(questions, perf_data, exam_dates, tags):
    if not tags:
        clear_screen()
        print("[No hay etiquetas]")
        press_any_key()
        return
    while True:
        clear_screen()
        print("\n=== Etiquetas disponibles ===")
        for i, t in enumerate(tags, start=1):
            print(f"{i}) {t}")
        print("0) Volver")
        sel = input("Selecciona etiqueta: ").strip()
        if sel == "0":
            return
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(tags):
                comando_quiz_programado(
                    questions, perf_data, exam_dates, tag_filter=tags[idx]
                )
                return
        except ValueError:
            pass


def comando_estadisticas(questions, perf_data, cursos_dict):
    def mostrar(qids, titulo):
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
        print(f"\n=== Estadísticas: {titulo} ===")
        print(f"Total preguntas: {total}")
        print(f"Sin intentar: {never}")
        print(f"Saltadas: {skipped}")
        print(f"Incorrectas: {wrong}")
        print(f"Correctas: {correct}\n")
        press_any_key()

    while True:
        clear_screen()
        print("\n=== Estadísticas generales ===")
        print("1) Todo el repositorio")
        print("2) Curso")
        print("3) Archivo")
        print("4) Volver")
        op = input("Elige opción: ").strip()
        if op == "1":
            mostrar(list(range(len(questions))), "Repositorio completo")
        elif op == "2":
            cursos = sorted(cursos_dict.keys())
            while True:
                clear_screen()
                print("\n=== Cursos ===")
                for i, c in enumerate(cursos, start=1):
                    print(f"{i}) {c}")
                print("0) Volver")
                s = input("Selecciona curso: ").strip()
                if s == "0":
                    break
                try:
                    ci = int(s) - 1
                    if 0 <= ci < len(cursos):
                        cur = cursos[ci]
                        qids = [
                            idx for idx, q in enumerate(questions)
                            if os.path.relpath(q["_quiz_source"], QUIZ_DATA_FOLDER)
                               .split(os.sep)[0] == cur
                        ]
                        mostrar(qids, f"Curso {cur}")
                        break
                except ValueError:
                    pass
        elif op == "3":
            f = pick_a_file_menu(cursos_dict)
            if not f:
                continue
            qids = [idx for idx, q in enumerate(questions) if q["_quiz_source"] == f]
            mostrar(qids, f"Archivo {os.path.basename(f)}")
        elif op == "4":
            break


def mostrar_menu():
    clear_screen()
    print(f"QuizProg v{VERSION}")
    print(f"Carpeta de quizzes: '{QUIZ_DATA_FOLDER}'\n")
    print("1) Programadas para hoy")
    print("2) Todas las preguntas")
    print("3) No respondidas")
    print("4) Falladas")
    print("5) Falladas o saltadas")
    print("6) Por archivo")
    print("7) Por etiqueta")
    print("8) Resumen de archivos")
    print("9) Estadísticas")
    print("0) Salir")


def main():
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s:%(name)s:%(message)s")
    set_title(f"QuizProg v{VERSION}")
    clear_screen()
    press_any_key()

    questions, cursos_dict, quiz_files_info = load_all_quizzes(QUIZ_DATA_FOLDER)
    perf_data = load_performance_data()
    exam_dates = cargar_fechas_examen()
    tags = sorted({t for q in questions for t in q.get("tags", [])})

    while True:
        mostrar_menu()
        choice = input("Elige opción: ").strip()
        if choice == "1":
            comando_quiz_programado(questions, perf_data, exam_dates)
        elif choice == "2":
            comando_quiz_todas(questions, perf_data, exam_dates)
        elif choice == "3":
            comando_quiz_no_respondidas(questions, perf_data, exam_dates)
        elif choice == "4":
            comando_quiz_falladas(questions, perf_data, exam_dates)
        elif choice == "5":
            comando_quiz_falladas_o_saltadas(questions, perf_data, exam_dates)
        elif choice == "6":
            comando_quiz_por_archivo(questions, perf_data, cursos_dict, exam_dates)
        elif choice == "7":
            comando_quiz_por_etiqueta(questions, perf_data, exam_dates, tags)
        elif choice == "8":
            comando_resumen_archivos(questions, perf_data, cursos_dict, quiz_files_info)
        elif choice == "9":
            comando_estadisticas(questions, perf_data, cursos_dict)
        elif choice == "0":
            clear_screen()
            print("¡Hasta luego!")
            sys.exit(0)


if __name__ == "__main__":
    main()
