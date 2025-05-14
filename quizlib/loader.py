# quizlib/loader.py

import os
import sys
import json
import logging
import hashlib

QUIZ_DATA_FOLDER = os.environ.get("QUIZ_DATA_FOLDER", "quiz_data")
INDEX_FILENAME = ".quiz_index.json"

logger = logging.getLogger(__name__)


def fingerprint_question(q):
    """
    Normalize a question + its answers and return a stable SHA256 fingerprint.
    """
    core = {
        "question": q.get("question", "").strip(),
        "answers": sorted(
            [
                {"text": a.get("text", "").strip(), "correct": bool(a.get("correct", False))}
                for a in q.get("answers", [])
            ],
            key=lambda x: (x["text"], x["correct"])
        )
    }
    raw = json.dumps(core, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_index(folder):
    """
    Load the on-disk index of questions, or initialize a fresh one if missing/corrupt.
    """
    path = os.path.join(folder, INDEX_FILENAME)
    if not os.path.exists(path):
        return {
            "next_id": 1,
            "files": {},
            "fingerprint_to_id": {},
            "archived": []
        }
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return {
                "next_id": data.get("next_id", 1),
                "files": data.get("files", {}),
                "fingerprint_to_id": data.get("fingerprint_to_id", {}),
                "archived": data.get("archived", [])
            }
    except Exception as ex:
        logger.warning(f"Could not load quiz-index at {path}: {ex}. Reinitializing.")
        return {
            "next_id": 1,
            "files": {},
            "fingerprint_to_id": {},
            "archived": []
        }


def save_index(folder, index_data):
    """
    Write the index back to disk.
    """
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, INDEX_FILENAME)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        logger.error(f"Failed to save quiz-index at {path}: {ex}")


def load_json_file(filepath):
    """
    Load a JSON file or return None if it fails; logs a warning.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
            if data.get("disabled"):
                # <-- NEW: skip any quiz marked disabled
                return None
            if "questions" not in data:
                logger.warning(f"Missing 'questions' in JSON {filepath}; skipping.")
                return None
            return data
    except Exception as ex:
        logger.warning(f"Error loading JSON from {filepath}; skipping. ({ex})")
        return None


def discover_quiz_files(folder):
    """Recursively find all `.json` files under `folder`."""
    quiz_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json"):
                quiz_files.append(os.path.join(root, f))
    return quiz_files


def load_all_quizzes(folder=QUIZ_DATA_FOLDER):
    """
    Returns (combined_questions, cursos_dict, quiz_files_info), but
    now indexing each question with a stable `_quiz_id` and tracking archive.
    Quizzes with top-level `"disabled": true` are ignored.
    """
    # 1) Load or init the index
    index = load_index(folder)
    new_index = {
        "next_id": index["next_id"],
        "files": {},
        "fingerprint_to_id": dict(index["fingerprint_to_id"]),
        "archived": list(index["archived"])
    }

    # 2) Discover files
    all_files = discover_quiz_files(folder)
    if not all_files:
        print(f"No se encontraron archivos JSON en '{folder}'!")
        sys.exit(1)

    seen_relpaths = set()

    # 3) For each file, update index entries
    for filepath in all_files:
        rel = os.path.relpath(filepath, folder)
        seen_relpaths.add(rel)
        try:
            mtime = os.path.getmtime(filepath)
        except OSError:
            mtime = None

        old_entry = index["files"].get(rel)
        if old_entry and old_entry.get("mtime") == mtime:
            # Unchanged: reuse the question list
            new_index["files"][rel] = old_entry
        else:
            # New or modified file: (re)compute fingerprints → IDs
            data = load_json_file(filepath)
            if not data:
                # disabled or invalid → archive any old questions
                if old_entry:
                    for e in old_entry.get("questions", []):
                        if e["id"] not in new_index["archived"]:
                            new_index["archived"].append(e["id"])
                continue

            qlist = data.get("questions", [])
            q_entries = []
            for q in qlist:
                fp = fingerprint_question(q)
                if fp in new_index["fingerprint_to_id"]:
                    qid = new_index["fingerprint_to_id"][fp]
                else:
                    qid = new_index["next_id"]
                    new_index["fingerprint_to_id"][fp] = qid
                    new_index["next_id"] += 1
                q_entries.append({"fingerprint": fp, "id": qid})

            # Archive any questions dropped from this file
            if old_entry:
                old_ids = {e["id"] for e in old_entry.get("questions", [])}
                new_ids = {e["id"] for e in q_entries}
                for dropped in old_ids - new_ids:
                    if dropped not in new_index["archived"]:
                        new_index["archived"].append(dropped)

            new_index["files"][rel] = {
                "mtime": mtime,
                "questions": q_entries
            }

    # 4) Archive any files that disappeared entirely
    for old_rel, old_entry in index["files"].items():
        if old_rel not in seen_relpaths:
            for e in old_entry.get("questions", []):
                qid = e["id"]
                if qid not in new_index["archived"]:
                    new_index["archived"].append(qid)

    # 5) Persist index
    save_index(folder, new_index)

    # 6) Build combined_questions, cursos_dict, quiz_files_info,
    #    skipping any disabled files
    cursos_dict = {}
    combined_questions = []
    quiz_files_info = []

    for filepath in all_files:
        data = load_json_file(filepath)
        if not data:
            continue  # either disabled or invalid

        questions_list = data["questions"]
        count = len(questions_list)
        quiz_files_info.append({
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "question_count": count
        })

        # Determine course/section
        rel_path = os.path.relpath(filepath, folder)
        parts = rel_path.split(os.sep)
        curso = parts[0] if parts else "(Unknown)"
        section = parts[1] if len(parts) > 2 else None

        cursos_dict.setdefault(curso, {
            "sections": {}, "total_files": 0, "total_questions": 0
        })
        cursos_dict[curso]["total_files"] += 1
        cursos_dict[curso]["total_questions"] += count

        sect_name = section if section else "(No subfolder)"
        sec = cursos_dict[curso]["sections"].setdefault(sect_name, {
            "files": [], "section_questions": 0
        })
        sec["files"].append({
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "question_count": count
        })
        sec["section_questions"] += count

        # Merge questions, injecting `_quiz_id`
        for q in questions_list:
            fp = fingerprint_question(q)
            q["_quiz_source"] = filepath
            q["_quiz_id"] = new_index["fingerprint_to_id"][fp]
            combined_questions.append(q)

    return combined_questions, cursos_dict, quiz_files_info
