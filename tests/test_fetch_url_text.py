from unittest.mock import Mock, patch
import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from components.wizard import fetch_url_text


def test_fetch_url_text_job_html() -> None:
    html = "<html><head><title>Dev</title></head><body>Join us</body></html>"
    mock_resp = Mock(status_code=200, text=html, headers={"content-type": "text/html"})
    doc_inst = Mock()
    doc_inst.summary.return_value = "<article>Join us</article>"
    with (
        patch("components.wizard.requests.get", return_value=mock_resp),
        patch("components.wizard.Document", return_value=doc_inst),
    ):
        text = fetch_url_text("http://example.com/job")
    assert "Join us" in text
