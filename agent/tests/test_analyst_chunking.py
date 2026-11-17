from src.analysis.chunking import is_truncation_error, split_chunk


def test_split_analysis_chunk_preserves_content():
    text = "palabra " * 2000
    parts = split_chunk(text)

    assert parts is not None
    left, right = parts
    assert left + " " + right == text.strip()
    assert left
    assert right


def test_truncation_error_is_detected():
    error = Exception(
        "Could not parse response content as the length limit was reached"
    )

    assert is_truncation_error(error)
