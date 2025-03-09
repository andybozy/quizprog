# quizlib/navigator.py

import os

def pick_a_file_menu(cursos_dict):
    """
    Interactively lets the user pick:
      1) A course
      2) A section (if any)
      3) A file
    Returns the full file path (string) or None if canceled or no valid choice.
    """
    if not cursos_dict:
        print("No hay cursos disponibles.")
        return None

    # Step 1: Choose Course
    course_names = sorted(cursos_dict.keys())
    while True:
        print("\n=== Lista de Cursos ===")
        for i, cname in enumerate(course_names, start=1):
            print(f"{i}) {cname}")
        print("0) Cancelar\n")
        choice = input("Selecciona un curso: ").strip()
        if choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(course_names):
                chosen_course = course_names[idx]
                break
        except ValueError:
            pass
        print("Opción no válida, intenta de nuevo.")

    # Step 2: Choose Section
    course_data = cursos_dict[chosen_course]
    section_names = sorted(course_data["sections"].keys())
    if not section_names:
        # no sections at all
        # We'll treat that as a single section named "(No subfolder)"
        return _pick_file_from_section(chosen_course, "(No subfolder)", course_data["sections"])
    else:
        while True:
            print(f"\n=== Secciones de '{chosen_course}' ===")
            for i, sname in enumerate(section_names, start=1):
                print(f"{i}) {sname}")
            print("0) Cancelar\n")
            choice = input("Selecciona una sección: ").strip()
            if choice == "0":
                return None
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(section_names):
                    chosen_section = section_names[idx]
                    break
            except ValueError:
                pass
            print("Opción no válida, intenta de nuevo.")

        # Step 3: Pick the file
        return _pick_file_from_section(chosen_course, chosen_section, course_data["sections"])


def _pick_file_from_section(chosen_course, chosen_section, sections_dict):
    """Helper to list files in the chosen section, let user pick one."""
    if chosen_section not in sections_dict:
        print("No existe la sección seleccionada.")
        return None

    file_list = sections_dict[chosen_section]["files"]
    if not file_list:
        print("No hay archivos en esta sección.")
        return None

    while True:
        print(f"\n=== Archivos en '{chosen_section}' ({chosen_course}) ===")
        for i, fobj in enumerate(file_list, start=1):
            print(f"{i}) {fobj['filename']}  ({fobj['question_count']} preguntas)")
        print("0) Cancelar\n")
        choice = input("Selecciona un archivo: ").strip()
        if choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(file_list):
                return file_list[idx]["filepath"]
        except ValueError:
            pass
        print("Opción no válida, intenta de nuevo.")


def get_file_question_count(questions, filepath):
    """Return how many questions come from a specific file."""
    return sum(1 for q in questions if q.get("_quiz_source") == filepath)
