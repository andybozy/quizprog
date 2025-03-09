#tests/test_main.py

import pytest
import pexpect
import os
import tempfile
import json

@pytest.mark.skipif(os.name == "nt", reason="pexpect more complex on Windows")
def test_main_startup():
    with tempfile.TemporaryDirectory() as temp_quiz_folder:
        # create a quiz file
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

        os.environ["QUIZ_DATA_FOLDER"] = temp_quiz_folder

        # Run the main entry point
        child = pexpect.spawn("python -m quizlib.main", encoding="utf-8", timeout=10)

        # Expect version line
        child.expect("QuizProg v", timeout=5)
        # Prompt "Presiona Enter para continuar..."
        child.expect("Presiona Enter para continuar...", timeout=5)
        # Press Enter
        child.sendline("")

        # Should print "Archivos de Quiz Cargados"
        child.expect("Archivos de Quiz Cargados", timeout=5)

        # Choose "6) Salir" to confirm it works
        child.expect("Selecciona una opción", timeout=5)
        child.sendline("6")
        child.expect("¡Hasta luego!", timeout=5)
        child.expect(pexpect.EOF, timeout=5)


@pytest.mark.skipif(os.name == "nt", reason="pexpect more complex on Windows")
def test_menu_select_file_and_submenu():
    """
    Verifies that when the user picks option "4) Seleccionar un archivo",
    then we see the sub-menu (1,2,3,4) for the chosen file.
    """
    with tempfile.TemporaryDirectory() as temp_quiz_folder:
        # create a quiz file
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

        os.environ["QUIZ_DATA_FOLDER"] = temp_quiz_folder

        child = pexpect.spawn("python -m quizlib.main", encoding="utf-8", timeout=10)
        child.expect("QuizProg v", timeout=5)
        child.expect("Presiona Enter para continuar...", timeout=5)
        child.sendline("")

        # "Archivos de Quiz Cargados"
        child.expect("Archivos de Quiz Cargados", timeout=5)

        # In main menu, pick "4" => Seleccionar un archivo específico
        child.expect("Selecciona una opción", timeout=5)
        child.sendline("4")

        # We'll see the "=== Lista de Cursos ===" prompt
        child.expect("Lista de Cursos", timeout=5)
        # There's only one course folder by default => pick "1"
        child.sendline("1")

        # Possibly one section => pick "1"
        child.expect("Selecciona una sección", timeout=5)
        child.sendline("1")

        # We'll see the file selection prompt => pick "1"
        child.expect("Selecciona un archivo", timeout=5)
        child.sendline("1")

        # Now we should see the sub-menu with 1..4
        child.expect("Filtro para el archivo seleccionado", timeout=5)
        child.expect("1\\) Realizar quiz con TODAS las preguntas", timeout=5)
        child.expect("2\\) Realizar quiz con preguntas NO respondidas", timeout=5)
        child.expect("3\\) Realizar quiz con preguntas FALLADAS", timeout=5)
        child.expect("4\\) Volver al menú principal", timeout=5)

        # We'll pick "4" => go back to main menu
        child.sendline("4")

        # Now in main menu again => pick "6" => Salir
        child.expect("Selecciona una opción", timeout=5)
        child.sendline("6")
        child.expect("¡Hasta luego!", timeout=5)
        child.expect(pexpect.EOF, timeout=5)
