import pytest
import quizlib.main as mainmod
from quizlib.main import comando_quiz_por_etiqueta, comando_estadisticas

@pytest.fixture(autouse=True)
def suppress_io(monkeypatch):
    monkeypatch.setattr(mainmod, "clear_screen", lambda: None)
    monkeypatch.setattr(mainmod, "press_any_key", lambda: None)

def test_comando_quiz_por_etiqueta_no_tags(capsys):
    # No tags → should print "[No hay etiquetas]"
    comando_quiz_por_etiqueta([], {}, {}, [])
    captured = capsys.readouterr()
    assert "[No hay etiquetas]" in captured.out

def test_comando_quiz_por_etiqueta_with_tags(monkeypatch):
    questions = []
    perf_data = {}
    exam_dates = {}
    tags = ["tag1", "tag2"]
    # Simulate selecting the second tag
    inputs = iter(["2"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    called = {}
    def fake_due(questions_arg, perf_data_arg, exam_dates_arg, tag_filter, **kwargs):
        called["filter"] = tag_filter
    monkeypatch.setattr(mainmod, "comando_quiz_programado", fake_due)

    comando_quiz_por_etiqueta(questions, perf_data, exam_dates, tags)
    assert called.get("filter") == "tag2"

def test_comando_estadisticas_repo(monkeypatch, capsys):
    questions = [{"_quiz_source":"f"}]*3
    perf_data = {
        "0": {"history":[]},
        "1": {"history":["skipped"]},
        "2": {"history":["wrong","correct"]}
    }
    cursos_dict = {}
    # Simulate: choose "1) To do el repositorio", press Enter, then "4) Volver"
    inputs = iter(["1", "", "4"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    comando_estadisticas(questions, perf_data, cursos_dict)
    out = capsys.readouterr().out

    assert "Total preguntas: 3" in out
    assert "Sin intentar: 1" in out
    assert "Saltadas: 1" in out
    assert "Incorrectas: 0" in out
    assert "Correctas: 1" in out
