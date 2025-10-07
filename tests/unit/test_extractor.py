"""Tests for code extraction."""

from codegen_bench.parsing.extractor import CodeExtractor


def test_extract_markdown_blocks_single():
    """Test extracting single markdown code block."""
    text = """Here is the solution:

```c:src/main.c
int main() {
    return 0;
}
```
"""
    files = CodeExtractor.extract_markdown_blocks(text)
    assert len(files) == 1
    assert "src/main.c" in files
    assert "int main()" in files["src/main.c"]
    assert "return 0;" in files["src/main.c"]


def test_extract_markdown_blocks_multiple():
    """Test extracting multiple markdown code blocks."""
    text = """Here are the files:

```c:src/main.c
int main() {
    return 0;
}
```

Some explanation.

```c:src/helper.c
void helper() {
}
```
"""
    files = CodeExtractor.extract_markdown_blocks(text)
    assert len(files) == 2
    assert "src/main.c" in files
    assert "src/helper.c" in files


def test_extract_markdown_blocks_no_colon():
    """Test markdown blocks without file path are ignored."""
    text = """```c
int main() {
    return 0;
}
```
"""
    files = CodeExtractor.extract_markdown_blocks(text)
    assert len(files) == 0


def test_extract_markdown_blocks_empty():
    """Test empty text returns empty dict."""
    files = CodeExtractor.extract_markdown_blocks("")
    assert files == {}


def test_extract_xml_tags_single():
    """Test extracting single XML file tag."""
    text = """<file path="src/main.c">
int main() {
    return 0;
}
</file>"""
    files = CodeExtractor.extract_xml_tags(text)
    assert len(files) == 1
    assert "src/main.c" in files
    assert "int main()" in files["src/main.c"]


def test_extract_xml_tags_multiple():
    """Test extracting multiple XML file tags."""
    text = """<file path="src/main.c">
int main() {
    return 0;
}
</file>

<file path="src/helper.c">
void helper() {}
</file>"""
    files = CodeExtractor.extract_xml_tags(text)
    assert len(files) == 2
    assert "src/main.c" in files
    assert "src/helper.c" in files


def test_extract_xml_tags_empty():
    """Test empty text returns empty dict."""
    files = CodeExtractor.extract_xml_tags("")
    assert files == {}


def test_extract_comment_markers_single():
    """Test extracting with comment markers."""
    text = """// FILE: src/main.c
int main() {
    return 0;
}
// END FILE"""
    files = CodeExtractor.extract_comment_markers(text)
    assert len(files) == 1
    assert "src/main.c" in files
    assert "int main()" in files["src/main.c"]


def test_extract_comment_markers_python_style():
    """Test extracting with Python-style comment markers."""
    text = """# FILE: main.py
def main():
    pass
# END FILE"""
    files = CodeExtractor.extract_comment_markers(text)
    assert len(files) == 1
    assert "main.py" in files
    assert "def main():" in files["main.py"]


def test_extract_comment_markers_multiple():
    """Test extracting multiple files with comment markers."""
    text = """// FILE: src/main.c
int main() {
    return 0;
}
// END FILE

// FILE: src/helper.c
void helper() {}
// END FILE"""
    files = CodeExtractor.extract_comment_markers(text)
    assert len(files) == 2
    assert "src/main.c" in files
    assert "src/helper.c" in files


def test_extract_comment_markers_no_end():
    """Test extracting without END FILE marker."""
    text = """// FILE: src/main.c
int main() {
    return 0;
}"""
    files = CodeExtractor.extract_comment_markers(text)
    assert len(files) == 1
    assert "src/main.c" in files


def test_extract_all_markdown():
    """Test extract_all with markdown format."""
    text = """```c:src/main.c
int main() {
    return 0;
}
```"""
    files = CodeExtractor.extract_all(text)
    assert len(files) == 1
    assert "src/main.c" in files


def test_extract_all_xml():
    """Test extract_all with XML format."""
    text = """<file path="src/main.c">
int main() {
    return 0;
}
</file>"""
    files = CodeExtractor.extract_all(text)
    assert len(files) == 1
    assert "src/main.c" in files


def test_extract_all_comments():
    """Test extract_all with comment markers."""
    text = """// FILE: src/main.c
int main() {
    return 0;
}
// END FILE"""
    files = CodeExtractor.extract_all(text)
    assert len(files) == 1
    assert "src/main.c" in files


def test_extract_all_mixed():
    """Test extract_all with mixed formats (markdown takes precedence)."""
    text = """```c:src/main.c
from markdown
```

<file path="src/helper.c">
from xml
</file>

// FILE: src/util.c
from comments
// END FILE"""
    files = CodeExtractor.extract_all(text)
    assert len(files) == 3
    assert "from markdown" in files["src/main.c"]
    assert "from xml" in files["src/helper.c"]
    assert "from comments" in files["src/util.c"]


def test_extract_all_precedence():
    """Test that markdown takes precedence over other formats."""
    text = """<file path="main.c">
from xml
</file>

```c:main.c
from markdown
```"""
    files = CodeExtractor.extract_all(text)
    assert len(files) == 1
    assert "from markdown" in files["main.c"]
    assert "from xml" not in files["main.c"]
