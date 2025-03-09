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

        child = pexpect.spawn("python main.py", encoding="utf-8", timeout=10)

        # 1) Expect 'QuizProg v'
        child.expect("QuizProg v", timeout=5)
        # 2) Expect "Presiona Enter para continuar..."
        child.expect("Presiona Enter para continuar...", timeout=5)

        # 3) Press Enter
        child.sendline("")

        # 4) Now main.py should print "Archivos de Quiz Cargados"
        child.expect("Archivos de Quiz Cargados", timeout=5)

        # Now we've confirmed it loaded successfully, let's exit
        # Next the code prints the main menu. We'll select "6" to exit.
        child.expect("Selecciona una opción", timeout=5)
        child.sendline("6")
        # This should print "¡Hasta luego!"
        child.expect("¡Hasta luego!", timeout=5)
        child.expect(pexpect.EOF, timeout=5)
