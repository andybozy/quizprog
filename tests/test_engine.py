import pytest
import random
from quizlib.engine import sanitize_question_text


def test_sanitize_question_text():
    text = """1) Something here

a) Option A
b) Option B
c) Option C
d) Option D
"""
    sanitized = sanitize_question_text(text)
    # We expect lines starting with 'a)', 'b)', 'c)', 'd)' to be removed
    assert "Option A" not in sanitized
    assert "Option B" not in sanitized
    assert "Option C" not in sanitized
    assert "Option D" not in sanitized
    # We do expect "Something here"
    assert "Something here" in sanitized


def test_shuffle_preserves_correctness():
    """
    Test that reshuffling the answers for a question preserves the set of correct answers.
    For example, if originally answers A and C are correct, then after shuffling,
    the set of correct answers (regardless of their new positions) remains the same.
    """
    original_answers = [
        {"text": "Option A", "correct": True},
        {"text": "Option B", "correct": False},
        {"text": "Option C", "correct": True},
        {"text": "Option D", "correct": False},
    ]
    # Capture the set of correct answer texts from the original order.
    correct_original = {ans["text"] for ans in original_answers if ans["correct"]}

    # Create a copy and shuffle it.
    shuffled_answers = original_answers[:]
    random.shuffle(shuffled_answers)
    correct_shuffled = {ans["text"] for ans in shuffled_answers if ans["correct"]}

    assert correct_shuffled == correct_original, (
        "After shuffling, the set of correct answers must remain unchanged."
    )


def test_shuffle_determinism_and_order_change():
    """
    Test that using a fixed random seed produces a deterministic shuffle and that generally,
    the order of answers is changed compared to the original order.
    """
    original_answers = [
        {"text": "Option A", "correct": True},
        {"text": "Option B", "correct": False},
        {"text": "Option C", "correct": True},
        {"text": "Option D", "correct": False},
    ]
    # With a fixed seed, the shuffled order should be deterministic.
    random.seed(42)
    shuffled1 = original_answers[:]
    random.shuffle(shuffled1)
    order1 = [ans["text"] for ans in shuffled1]

    random.seed(42)
    shuffled2 = original_answers[:]
    random.shuffle(shuffled2)
    order2 = [ans["text"] for ans in shuffled2]

    assert order1 == order2, "Shuffling with the same fixed seed must produce the same order."

    # Now, check that in general the order differs from the original order.
    random.seed()  # reset to system seed
    shuffled3 = original_answers[:]
    random.shuffle(shuffled3)
    order3 = [ans["text"] for ans in shuffled3]

    # In the unlikely event the shuffle equals the original order, reshuffle once more.
    if order3 == [ans["text"] for ans in original_answers]:
        random.shuffle(shuffled3)
        order3 = [ans["text"] for ans in shuffled3]
    assert order3 != [ans["text"] for ans in original_answers], (
        "Shuffled order should be different from the original order."
    )
def test_preguntar_multiple_correct(monkeypatch):
    """
    Test that for a question with two correct answers (e.g., A and B originally),
    after shuffling the answers the correct answer mapping is updated accordingly.
    The test simulates a user entering the new correct letters.
    """
    # Define a dummy question with two correct answers.
    question_data = {
        "question": "Test multi-correct question",
        "answers": [
            {"text": "Option A", "correct": True},
            {"text": "Option B", "correct": True},
            {"text": "Option C", "correct": False},
            {"text": "Option D", "correct": False}
        ],
        "explanation": "Options A and B are correct."
    }

    # Fix the random seed so that shuffle is deterministic.
    import random
    random.seed(123)
    # Simulate the shuffling as done in preguntar().
    answers_shuffled = question_data["answers"][:]
    random.shuffle(answers_shuffled)
    # Determine the new positions of the correct answers.
    correct_indices = [i for i, ans in enumerate(answers_shuffled) if ans.get("correct", False)]
    LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    correct_letters = [LETTERS[i] for i in correct_indices]
    # Join the letters with a comma (user might input "A,B" or "A, B")
    expected_input = ",".join(correct_letters)

    # Monkey-patch input() to return the expected correct answer.
    inputs = iter([expected_input])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    # Override clear_screen and press_any_key so they don't pause the test.
    monkeypatch.setattr("quizlib.engine.clear_screen", lambda: None)
    monkeypatch.setattr("quizlib.engine.press_any_key", lambda: None)

    # Update the question's answers to our shuffled order.
    question_data["answers"] = answers_shuffled

    # Prepare dummy performance data and session counts.
    perf_data = {}
    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}

    # Import and call preguntar.
    from quizlib.engine import preguntar
    result = preguntar(0, question_data, perf_data, session_counts)

    assert result is True, (
        "After shuffling, the engine should accept the answer corresponding to the correct answers."
    )
