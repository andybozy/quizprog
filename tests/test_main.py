# tests/test_main.py

import pytest
import pexpect
import os
import tempfile
import json


@pytest.mark.skipif(os.name == "nt", reason="pexpect more complex on Windows")
def test_main_startup():
    # Create a temporary quiz folder with a dummy quiz file.
    with tempfile.TemporaryDirectory() as temp_quiz_folder:
        # Create a subfolder (e.g., "test") and a dummy quiz file in it.
        test_subfolder = os.path.join(temp_quiz_folder, "test")
        os.makedirs(test_subfolder)
        quiz_file = os.path.join(test_subfolder, "dummy_quiz.json")
        dummy_quiz = {
            "questions": [
                {
                    "question": "Pregunta de prueba:\n\n¿Cuál es 2+2?",
                    "answers": [
                        {"text": "3", "correct": False},
                        {"text": "4", "correct": True},
                        {"text": "5", "correct": False},
                        {"text": "6", "correct": False}
                    ],
                    "explanation": "2+2 es 4."
                }
            ]
        }
        with open(quiz_file, "w", encoding="utf-8") as f:
            json.dump(dummy_quiz, f, indent=2, ensure_ascii=False)

        # Set environment variable so that the loader uses our temporary folder.
        os.environ["QUIZ_DATA_FOLDER"] = temp_quiz_folder

        # Spawn main.py.
        child = pexpect.spawn("python main.py", encoding="utf-8", timeout=10)

        # Expect that main.py prints the version or menu text.
        child.expect("QuizProg v", timeout=5)
        # Now send a command to exit (option "5" for Salir in our updated menu).
        child.sendline("5")
        child.expect("¡Hasta luego!", timeout=5)
        child.expect(pexpect.EOF, timeout=5)
