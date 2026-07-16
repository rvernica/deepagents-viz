from pathlib import Path

from deepagents_viz.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_stdout(capsys):
    code = main([str(FIXTURES / "simple")])
    assert code == 0
    out = capsys.readouterr().out
    assert "graph TD" in out
    assert '-->|"sub-agent (task)"| researcher' in out


def test_cli_writes_file(tmp_path):
    out_file = tmp_path / "diagram.mmd"
    code = main([str(FIXTURES / "simple"), "--output", str(out_file)])
    assert code == 0
    assert "graph TD" in out_file.read_text()


def test_cli_bad_target_returns_2(capsys):
    code = main(["/no/such/path"])
    assert code == 2
    assert "Cannot interpret target" in capsys.readouterr().err


def test_cli_short_output_flag(tmp_path):
    out_file = tmp_path / "d.mmd"
    code = main([str(FIXTURES / "simple"), "-o", str(out_file)])
    assert code == 0
    assert "graph TD" in out_file.read_text()


def test_cli_graph_option(capsys):
    code = main([str(FIXTURES / "simple"), "--graph", "agent"])
    assert code == 0
    assert "graph TD" in capsys.readouterr().out


def test_cli_file_attr_target(capsys):
    target = str(FIXTURES / "factory" / "agent.py") + ":make_graph"
    code = main([target])
    assert code == 0
    assert "factory-agent" in capsys.readouterr().out


def test_cli_user_code_error_returns_2(tmp_path, capsys):
    (tmp_path / "agent.py").write_text("raise ValueError('boom')\n")
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"agent": "./agent.py:agent"}}'
    )
    code = main([str(tmp_path)])
    assert code == 2
    assert "Failed to load target" in capsys.readouterr().err
