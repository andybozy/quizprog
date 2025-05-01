# QuizProg

**QuizProg** is a simple command‐line quiz program written in Python. It loads quiz data from JSON files and tracks your performance over time.

---

## Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/yourusername/quizprog.git
   cd quizprog
   ```

2. **(Optional) Create and activate a virtual environment**  
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # on Windows, use `venv\Scripts\activate`
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Install QuizProg**  
   ```bash
   # For a normal install:
   pip install .

   # Or for editable/development mode:
   pip install -e .
   ```

---

## Usage

By default, QuizProg looks for quiz files under `quiz_data/`. To point it at a different folder, set the `QUIZ_DATA_FOLDER` environment variable:

```bash
export QUIZ_DATA_FOLDER=/path/to/your/quizzes
```

Then launch the quiz with:

```bash
quizprog
```

—or, if you prefer—

```bash
python -m quizlib.main
```

You’ll be greeted with a menu:

```
=== QuizProg Main Menu ===
1) Realizar quiz con TODAS las preguntas
2) Realizar quiz con preguntas NO respondidas
3) Realizar quiz con preguntas FALLADAS (anteriores)
4) Seleccionar un archivo específico y realizar su quiz
5) Ver resumen de archivos cargados
6) Salir
```

- **Answering questions:** type the letter of your choice (e.g. `A`), or for multiple‐correct questions separate by commas/spaces/semicolons (e.g. `A,C` or `A C` or `A;C`).  
- **Exit a session early:** type `0` when prompted for an answer.  
- **Navigation:** press Enter at any “Presiona Enter para continuar…” prompt.

---

## JSON Quiz Format

Your quiz files must be valid JSON with a top‐level `questions` array. Each question needs at least:

```json
{
  "question": "¿2+2?",
  "answers": [
    { "text": "3", "correct": false },
    { "text": "4", "correct": true },
    { "text": "5", "correct": false },
    { "text": "6", "correct": false }
  ],
  "explanation": "Porque 2+2 es 4."
}
```

For full details on optional fields (lives, randomize, wrongmsg, etc.), see the [JSON Structure](#json-structure) section below.

---

## JSON Structure

- **title** (`string`, optional) – Quiz title  
- **description** (`string`, optional) – Shown before the quiz  
- **lives** (`int`, optional) – Max incorrect attempts  
- **randomize** (`bool`, optional) – Shuffle questions (`false` by default)  
- **questions** (`array`) – List of question objects:
  - **question** (`string`) – The prompt  
  - **answers** (`array`) – Exactly four objects, each with:
    - **text** (`string`)  
    - **correct** (`bool`)  
  - **explanation** (`string`, optional) – Shown after answering  
- And other optional top‐level or per‐question fields as described in the original docs.

---

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.
