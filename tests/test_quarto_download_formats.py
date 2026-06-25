from pathlib import Path

import yaml


def test_html_other_formats_include_docx() -> None:
    quarto_config = Path(__file__).resolve().parents[1] / "docs" / "_quarto.yml"
    config = yaml.safe_load(quarto_config.read_text(encoding="utf-8"))

    other_formats = config["format"]["html"]["other-formats"]
    assert "pdf" in other_formats
    assert "docx" in other_formats
