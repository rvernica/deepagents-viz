from pathlib import Path

from deepagents_viz.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_stdout(capsys):
    code = main([str(FIXTURES / "simple")])
    assert code == 0
    out = capsys.readouterr().out
    assert out.startswith("graph TD")
    assert "-->|task| researcher" in out


def test_cli_writes_file(tmp_path):
    out_file = tmp_path / "diagram.mmd"
    code = main([str(FIXTURES / "simple"), "--output", str(out_file)])
    assert code == 0
    assert out_file.read_text().startswith("graph TD")


def test_cli_bad_target_returns_2(capsys):
    code = main(["/no/such/path"])
    assert code == 2
    assert "Cannot interpret target" in capsys.readouterr().err
