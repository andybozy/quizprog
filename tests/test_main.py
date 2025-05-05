# tests/test_main.py

import pytest
import pexpect
import os
import tempfile
import json

@pytest.mark.skipif(os.name == "nt", reason="pexpect more complex on Windows")
def test_main_startup_and_exit():
    """Startup: press Enter, see menu, then choose 0 to exit."""
    with tempfile.TemporaryDirectory() as temp_quiz_folder:
        # Create a dummy quiz file under QUIZ_DATA_FOLDER
        test_dir = os.path.join(temp_quiz_folder, "test")
        os.makedirs(test_dir)
        quiz_file = os.path.join(test_dir, "dummy_quiz.json")
        dummy_data = {
            "questions": [
                {
                    "question": "¿2+2?",
                    "answers": [
                        {"text": "3", "correct": False},
                        {"text": "4", "correct": True},
                        {"text": "5", "correct": False},
                        {"text": "6", "correct": False}
                    ]
                }
            ]
        }
        with open(quiz_file, "w", encoding="utf-8") as f:
            json.dump(dummy_data, f, ensure_ascii=False, indent=2)

        # Point the program at our temp folder
        env = os.environ.copy()
        env["QUIZ_DATA_FOLDER"] = temp_quiz_folder

        # Spawn the app
        child = pexpect.spawn("python -m quizlib.main",
                              env=env,
                              encoding="utf-8",
                              timeout=10)

        # 1) Initial “Press Enter” prompt
        child.expect("Presiona Enter para continuar...", timeout=5)
        child.sendline("")

        # 2) Main menu appears
        child.expect("QuizProg v", timeout=5)
        child.expect("Elige opción:", timeout=5)

        # 3) Exit (option 0)
        child.sendline("0")
        child.expect("¡Hasta luego!", timeout=5)
        child.expect(pexpect.EOF, timeout=5)


@pytest.mark.skipif(os.name == "nt", reason="pexpect more complex on Windows")
def test_file_selection_submenu_and_return():
    """
    From main menu choose '6) Por archivo', drill into the quiz file submenu,
    then back out and finally exit.
    """
    with tempfile.TemporaryDirectory() as temp_quiz_folder:
        # Create a dummy quiz file under QUIZ_DATA_FOLDER
        test_dir = os.path.join(temp_quiz_folder, "test")
        os.makedirs(test_dir)
        quiz_file = os.path.join(test_dir, "dummy_quiz.json")
        dummy_data = {
            "questions": [
                {
                    "question": "¿2+2?",
                    "answers": [
                        {"text": "3", "correct": False},
                        {"text": "4", "correct": True}
                    ]
                }
            ]
        }
        with open(quiz_file, "w", encoding="utf-8") as f:
            json.dump(dummy_data, f, ensure_ascii=False, indent=2)

        env = os.environ.copy()
        env["QUIZ_DATA_FOLDER"] = temp_quiz_folder

        child = pexpect.spawn("python -m quizlib.main",
                              env=env,
                              encoding="utf-8",
                              timeout=10)

        # Initial prompt
        child.expect("Presiona Enter para continuar...", timeout=5)
        child.sendline("")

        # Main menu
        child.expect("QuizProg v", timeout=5)
        child.expect("Elige opción:", timeout=5)
        # Choose 6) Por archivo
        child.sendline("6")

        # Course list
        child.expect(r"=== Lista de Cursos ===", timeout=5)
        child.expect(r"1\) test", timeout=5)
        child.expect("Selecciona un curso:", timeout=5)
        child.sendline("1")

        # Only one "(No subfolder)" => skip section menu
        # Now file list
        child.expect(r"=== Archivos en '\(No subfolder\)' \(test\) ===", timeout=5)
        child.expect(r"1\) dummy_quiz.json", timeout=5)
        child.expect("Selecciona un archivo:", timeout=5)
        child.sendline("1")

        # File submenu
        child.expect(r"=== Selección de archivo ===", timeout=5)
        child.expect(r"1\) Todas", timeout=5)
        child.expect(r"2\) No respondidas", timeout=5)
        child.expect(r"3\) Falladas", timeout=5)
        child.expect(r"4\) Falladas o saltadas", timeout=5)
        child.expect(r"5\) Programadas para hoy", timeout=5)
        child.expect(r"6\) Volver", timeout=5)
        child.expect("Elige opción:", timeout=5)

        # Go back to main menu
        child.sendline("6")
        child.expect("QuizProg v", timeout=5)
        child.expect("Elige opción:", timeout=5)

        # Finally exit
        child.sendline("0")
        child.expect("¡Hasta luego!", timeout=5)
        child.expect(pexpect.EOF, timeout=5)
