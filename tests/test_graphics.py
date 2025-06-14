from unittest.mock import patch
import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from services.graphics import gen_standortkarte, gen_timeline_graphic


def test_gen_standortkarte_returns_id() -> None:
    with patch(
        "ace_tools.image_gen.text2im", return_value={"image_ids": ["img"]}
    ) as mock_gen:
        result = gen_standortkarte("Some Street 1")
    mock_gen.assert_called_once()
    assert result == "img"


def test_gen_timeline_graphic_returns_id() -> None:
    with patch(
        "ace_tools.image_gen.text2im", return_value={"image_ids": ["img2"]}
    ) as mock_gen:
        result = gen_timeline_graphic(["A", "B"])
    mock_gen.assert_called_once()
    assert result == "img2"
