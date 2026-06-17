import pytest
from app.rag.pipeline import format_docs

class MockDoc:
    def __init__(self, content):
        self.page_content = content

def test_format_docs():
    docs = [MockDoc("Doc 1"), MockDoc("Doc 2")]
    result = format_docs(docs)
    assert result == "Doc 1\n\nDoc 2"
