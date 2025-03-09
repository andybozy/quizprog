# quizlib/navigator.py

import os

def pick_a_file_menu(cursos_dict):
    """
    Interactively pick:
      1) A course
      2) A section
      3) A file
    Returns filepath or None if canceled.
    """
    if not cursos_dict:
        print("No hay cursos disponibles.")
        return None

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

    course_data = cursos_dict[chosen_course]
    section_names = sorted(course_data["sections"].keys())
    # If there's only one section and it's "(No subfolder)", skip
    if len(section_names) == 1 and section_names[0] == "(No subfolder)":
        chosen_section = section_names[0]
    else:
        if not section_names:
            print("No hay secciones en este curso.")
            return None
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

    return _pick_file_from_section(chosen_course, chosen_section, course_data["sections"])

def _pick_file_from_section(chosen_course, chosen_section, sections_dict):
    """List files in the chosen section, let user pick one."""
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
            print(f"{i}) {fobj['filename']} ({fobj['question_count']} preguntas)")
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

def print_quiz_files_summary(quiz_files_info):
    """Show all loaded quiz files by name and question count."""
    print("=== Archivos de Quiz Cargados ===")
    if not quiz_files_info:
        print("No se encontraron archivos de quiz.")
    else:
        for finfo in quiz_files_info:
            print(f"{finfo['filename']} - {finfo['question_count']} preguntas")
    print()
