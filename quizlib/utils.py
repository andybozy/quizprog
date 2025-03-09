# quizlib/utils.py

import os
import json

def clear_screen():
    """Cross-platform screen clear."""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    """Wait for user to press Enter."""
    input("\nPresiona Enter para continuar...")

def print_cursos_summary_detailed(cursos_dict):
    """
    Display a detailed summary of the course and section structure.
    """
    print("=== COURSES & SECTIONS ===\n")
    total_cursos = len(cursos_dict)
    total_files = 0
    total_questions = 0

    for curso, info in cursos_dict.items():
        c_files = info["total_files"]
        c_questions = info["total_questions"]
        total_files += c_files
        total_questions += c_questions

        print(f"Course: {curso} -> {c_files} file(s), {c_questions} question(s) total")
        for section_name, section_data in info["sections"].items():
            print(f"  Section: {section_name} -> {len(section_data['files'])} file(s), {section_data['section_questions']} question(s)")
            for file_info in section_data["files"]:
                print(f"    - {file_info['filename']} ({file_info['question_count']} questions)")
        print()

    print(f"TOTAL COURSES: {total_cursos}")
    print(f"TOTAL FILES: {total_files}")
    print(f"TOTAL QUESTIONS: {total_questions}\n")


def track_quiz_stats(session_counts):
    """
    Print the current statistics: correct, wrong, unanswered, and total questions.
    """
    correct = session_counts.get("correct", 0)
    wrong = session_counts.get("wrong", 0)
    unanswered = session_counts.get("unanswered", 0)
    total = correct + wrong + unanswered
    print(f"\nScore: Correct: {correct}, Wrong: {wrong}, Unanswered: {unanswered}, Total: {total}\n")
