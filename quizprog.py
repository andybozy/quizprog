import os
import json
import random
import sys
import traceback
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIG / CONSTANTS
# ---------------------------------------------------------------------------
QUIZ_DATA_FOLDER = "quiz_data"
PERFORMANCE_FILE = "quiz_performance.json"
VERSION = "2.0.0"

# ---------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def clear():
    """Cross-platform clear screen."""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    """Wait for user input to continue."""
    input("\nPress Enter to continue...")

def load_json_file(filepath):
    """Safely load JSON data from a file, returning None on failure."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"[!] Failed to load '{filepath}': {ex}")
        return None

# ---------------------------------------------------------------------------
# PERFORMANCE TRACKING
# ---------------------------------------------------------------------------
def load_performance_data():
    """
    Loads or initializes performance data from PERFORMANCE_FILE.
    The data structure is a dict with question_id as key and a dict of flags:
      { "wrong": bool, "unanswered": bool }.
    """
    if not os.path.exists(PERFORMANCE_FILE):
        return {}
    try:
        with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_performance_data(perf_data):
    """Persists the performance data to PERFORMANCE_FILE as JSON."""
    try:
        with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[!] Error saving performance data: {ex}")

# ---------------------------------------------------------------------------
# DATA LOADING: DISCOVER ALL JSON QUIZ FILES
# ---------------------------------------------------------------------------
def discover_quiz_files(folder):
    """
    Recursively walk `folder` (quiz_data/) to find all .json files.
    Returns a list of absolute paths.
    """
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files

def load_all_quizzes():
    """
    Loads and merges all quizzes from quiz_data into a single list of questions.
    The structure each question expects:
       {
         "question": str,
         "answers": [ { "text": str, "correct": bool }, ... ],
         "explanation": str (optional),
         "wrongmsg": str (optional, or it could be an object/dict),
         ...
         # you may add: "source", "legal_reference", etc.
       }
    Returns:
      quiz_questions: list of dicts (the combined questions)
      quiz_count: total question count
    """
    all_files = discover_quiz_files(QUIZ_DATA_FOLDER)
    if not all_files:
        print(f"No quiz JSON files found in '{QUIZ_DATA_FOLDER}'!")
        sys.exit(1)

    all_questions = []
    for filepath in all_files:
        data = load_json_file(filepath)
        if not data or "questions" not in data:
            continue

        # Some user-supplied JSONs have top-level "questions"
        # matching the new structure: question, answers = [...], etc.
        # We'll merge them into a single structure below:
        questions_list = data["questions"]
        for q in questions_list:
            # Validate minimal fields:
            if "question" not in q or "answers" not in q:
                continue  # skip if not well-formed
            # Store reference to which file it came from (optional):
            q["_quiz_source"] = filepath
            all_questions.append(q)

    return all_questions, len(all_questions)

# ---------------------------------------------------------------------------
# QUIZ LOGIC
# ---------------------------------------------------------------------------
def ask_question(qid, question_data, perf_data):
    """
    Presents one question to the user. Returns True if answered correctly,
    False if answered incorrectly, and None if not answered (e.g. user quit).
    Also updates perf_data with 'wrong' or 'unanswered' as needed.
    """

    # Mark as unanswered by default:
    if str(qid) not in perf_data:
        perf_data[str(qid)] = {"wrong": False, "unanswered": True}
    else:
        # If previously flagged 'wrong' or 'unanswered',
        # we keep it as is until we see if the user gets it right now.
        pass

    clear()

    question_text = question_data["question"]
    answers = question_data["answers"]  # list of { text, correct }
    explanation = question_data.get("explanation", "")
    # wrongmsg can be a string or something else, adapt as needed:
    wrongmsg = question_data.get("wrongmsg", "")

    # Collect indices of correct answers:
    correct_indices = [idx for idx, ans in enumerate(answers) if ans.get("correct")]

    # If none are correct or question is malformed, we skip.
    if not correct_indices:
        print(f"[!] This question has no correct answers? Skipping...\n")
        perf_data[str(qid)]["unanswered"] = False
        return True  # treat as correct skip

    # Single or multi-correct?
    multi_correct = (len(correct_indices) > 1)

    print(f"Q{qid}: {question_text}\n")
    for i, ans in enumerate(answers):
        print(f"[{i+1}] {ans['text']}")
    print("\n[0] Quit this quiz session\n")

    if multi_correct:
        print("NOTE: This question may have multiple correct answers.\n"
              "Enter each correct number separated by commas (e.g. '1,3')")

    user_input = input("Your answer: ").strip()
    if user_input == "0":
        # Mark question as unanswered if the user quits right away:
        perf_data[str(qid)]["unanswered"] = True
        return None  # user quit

    # Attempt to parse user input into integer(s)
    try:
        # e.g. '1,2' => [1,2]
        selected_indices = [int(x) - 1 for x in user_input.split(",")]
    except ValueError:
        # Invalid input => consider it a wrong attempt
        selected_indices = [-1]

    # Check correctness:
    # If single correct, we only allow one index:
    if not multi_correct:
        if len(selected_indices) == 1 and selected_indices[0] in correct_indices:
            # correct
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            # Show explanation if present:
            if explanation:
                clear()
                print("Correct!\n")
                print(f"Explanation:\n{explanation}\n")
                press_any_key()
            return True
        else:
            # wrong
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("Incorrect.\n")
            # Show question-level wrongmsg if present:
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            press_any_key()
            return False
    else:
        # multi-correct
        correct_set = set(correct_indices)
        user_set = set(selected_indices)

        if user_set == correct_set:  # must match exactly
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = False
            if explanation:
                clear()
                print("Correct!\n")
                print(f"Explanation:\n{explanation}\n")
                press_any_key()
            return True
        else:
            perf_data[str(qid)]["unanswered"] = False
            perf_data[str(qid)]["wrong"] = True
            clear()
            print("Incorrect.\n")
            if isinstance(wrongmsg, str) and wrongmsg:
                print(f"{wrongmsg}\n")
            press_any_key()
            return False

# ---------------------------------------------------------------------------
# MAIN QUIZ PLAY
# ---------------------------------------------------------------------------
def play_quiz(questions, perf_data, filter_mode="all"):
    """
    filter_mode can be:
      - "all": ask all questions
      - "wrong": only ask those flagged as 'wrong'
      - "unanswered": only ask those flagged as 'unanswered'
    Returns once user completes or quits.
    """

    # Filter questions:
    if filter_mode == "wrong":
        playable = []
        for i, q in enumerate(questions):
            # If question has an entry in perf_data with wrong=True, include it
            if str(i) in perf_data and perf_data[str(i)]["wrong"]:
                playable.append((i, q))
    elif filter_mode == "unanswered":
        playable = []
        for i, q in enumerate(questions):
            # If question not in perf_data or unanswered=True, include it
            if str(i) not in perf_data or perf_data[str(i)]["unanswered"]:
                playable.append((i, q))
    else:
        # "all" or fallback
        playable = [(i, q) for i, q in enumerate(questions)]

    if not playable:
        print("\n[No questions match the chosen filter. Returning to menu...]\n")
        press_any_key()
        return

    # Shuffle if desired:
    # random.shuffle(playable)  # If you want random order, uncomment

    idx = 0
    while idx < len(playable):
        qid, qdata = playable[idx]
        result = ask_question(qid, qdata, perf_data)
        save_performance_data(perf_data)  # save after each question
        if result is None:
            # user decided to quit the quiz
            break
        # proceed to next
        idx += 1

    clear()
    print("Quiz session ended.\n")
    press_any_key()

# ---------------------------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------------------------
def main():
    clear()
    print(f"QuizProg v{VERSION} - Merged Auto Quiz Loader\n")

    # 1) Load all quizzes:
    print("[1] Loading quizzes from 'quiz_data' folder...")
    questions, qcount = load_all_quizzes()

    # 2) Load or init performance data:
    perf_data = load_performance_data()

    # 3) Main loop:
    while True:
        clear()
        print(f"=== QUIZPROG v{VERSION} ===\n")
        print(f"Loaded {qcount} total questions from the 'quiz_data' folder.")
        print("Performance data is tracked across sessions.\n")

        print("[1] Take entire quiz (all questions)")
        print("[2] Review only unanswered questions")
        print("[3] Review only those got wrong before")
        print("[4] Reset performance data")
        print("[5] Exit\n")

        choice = input("Choose an option: ").strip()
        if choice == "1":
            play_quiz(questions, perf_data, filter_mode="all")
        elif choice == "2":
            play_quiz(questions, perf_data, filter_mode="unanswered")
        elif choice == "3":
            play_quiz(questions, perf_data, filter_mode="wrong")
        elif choice == "4":
            # Confirm reset:
            clear()
            confirm = input("Reset all performance data? (y/n) ").lower()
            if confirm == "y":
                perf_data.clear()
                save_performance_data(perf_data)
                print("Performance data has been reset.\n")
                press_any_key()
        elif choice == "5":
            print("Goodbye!")
            sys.exit(0)
        else:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        print("\n[!] Exiting due to KeyboardInterrupt...")
        sys.exit(0)
    except Exception as e:
        clear()
        print("[!] Unhandled exception:")
        traceback.print_exc()
        sys.exit(1)
