from unittest.mock import Mock, patch
import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from services.scraping_tools import scrape_company_site


def test_scrape_company_site_parses_title_and_description() -> None:
    html = (
        "<html><head><title>MyCo</title>"
        "<meta name='description' content='Great services'></head></html>"
    )
    mock_resp = Mock(status_code=200, text=html)
    with patch("requests.get", return_value=mock_resp):
        result = scrape_company_site("http://example.com")
    assert result == {"title": "MyCo", "description": "Great services"}
