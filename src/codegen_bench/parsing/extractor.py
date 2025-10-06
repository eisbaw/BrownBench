"""Extract code changes from LLM outputs."""

import re
from typing import Any


class CodeExtractor:
    """Extract code changes from various formats in LLM responses.

    Supports multiple extraction strategies:
    1. Markdown code blocks with file paths (```lang:path)
    2. XML-style file tags (<file path="...">)
    3. Comment-based file markers (// FILE: path)
    4. Diff format patches
    """

    @staticmethod
    def extract_markdown_blocks(text: str) -> dict[str, str]:
        """Extract code from markdown blocks with file paths.

        Parses blocks in the format:
        ```language:path/to/file.ext
        code content
        ```

        Args:
            text: Text containing markdown code blocks

        Returns:
            Dictionary mapping file paths to content
        """
        files = {}
        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            # Look for code block start with file path
            if line.startswith("```") and ":" in line:
                # Extract language and path
                parts = line[3:].split(":", 1)
                if len(parts) == 2:
                    path = parts[1].strip()
                    # Collect code until closing ```
                    code_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith("```"):
                        code_lines.append(lines[i])
                        i += 1
                    files[path] = "\n".join(code_lines)
            i += 1

        return files

    @staticmethod
    def extract_xml_tags(text: str) -> dict[str, str]:
        """Extract code from XML-style file tags.

        Parses tags in the format:
        <file path="path/to/file.ext">
        code content
        </file>

        Args:
            text: Text containing XML file tags

        Returns:
            Dictionary mapping file paths to content
        """
        files = {}
        pattern = r'<file\s+path="([^"]+)"\s*>(.*?)</file>'
        matches = re.findall(pattern, text, re.DOTALL)

        for path, content in matches:
            files[path] = content.strip()

        return files

    @staticmethod
    def extract_comment_markers(text: str) -> dict[str, str]:
        """Extract code from comment-based file markers.

        Parses markers in the format:
        // FILE: path/to/file.ext
        code content
        // END FILE

        Args:
            text: Text containing comment markers

        Returns:
            Dictionary mapping file paths to content
        """
        files = {}
        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            # Look for FILE marker
            if line.startswith("// FILE:") or line.startswith("# FILE:"):
                path = line.split(":", 1)[1].strip()
                code_lines = []
                i += 1
                # Collect until END FILE or next FILE marker
                while i < len(lines):
                    current = lines[i].strip()
                    if current in ["// END FILE", "# END FILE"] or current.startswith(
                        ("// FILE:", "# FILE:")
                    ):
                        break
                    code_lines.append(lines[i])
                    i += 1
                files[path] = "\n".join(code_lines).strip()
            i += 1

        return files

    @staticmethod
    def extract_all(text: str) -> dict[str, str]:
        """Try all extraction strategies and merge results.

        Args:
            text: Text containing code changes

        Returns:
            Dictionary mapping file paths to content
        """
        # Try all strategies
        markdown = CodeExtractor.extract_markdown_blocks(text)
        xml = CodeExtractor.extract_xml_tags(text)
        comments = CodeExtractor.extract_comment_markers(text)

        # Merge results (markdown takes precedence)
        files = {}
        files.update(comments)
        files.update(xml)
        files.update(markdown)

        return files
