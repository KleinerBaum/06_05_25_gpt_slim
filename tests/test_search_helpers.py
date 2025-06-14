from unittest.mock import patch

from logic.search_helpers import run_file_search, USE_CASE_QUERIES


def test_run_file_search_calls_msearch() -> None:
    with patch(
        "ace_tools.file_search.msearch", return_value={"results": ["hit"]}
    ) as mock_search:
        result = run_file_search(["doc1"])
    # called once per query
    assert mock_search.call_count == sum(len(q) for q in USE_CASE_QUERIES.values())
    # each tag should exist in result
    assert set(result.keys()) == set(USE_CASE_QUERIES.keys())
