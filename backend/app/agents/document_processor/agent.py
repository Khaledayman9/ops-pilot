from __future__ import annotations

from app.core import BaseAgent
from logger import logger
from markitdown import MarkItDown

from .models import DocumentProcessorInput, DocumentProcessorOutput


class DocumentProcessorAgent(BaseAgent):
    """
    Converts uploaded incident evidence into markdown using MarkItDown.
    Supports PDF, DOCX, PPTX, HTML, and other office/document formats.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("document_processor", **kwargs)
        self._converter = MarkItDown()

    async def run(self, inp: DocumentProcessorInput) -> DocumentProcessorOutput:
        self._log(f"Processing document filename={inp.filename}")

        if inp.inline_content is not None:
            markdown = inp.inline_content.strip()
            self._log(
                f"Inline passthrough mode: {len(markdown)} chars for {inp.filename}"
            )
            if not markdown:
                logger.warning(
                    f"[document_processor] Inline content empty for {inp.filename}"
                )
            return DocumentProcessorOutput(
                filename=inp.filename,
                markdown=markdown,
                chunks=1,
                characters=len(markdown),
                mime_type=inp.mime_type or "text/markdown",
            )

        self._log(f"Converting via MarkItDown: {inp.file_path}")
        result = self._converter.convert(inp.file_path)
        markdown = result.text_content.strip()

        if not markdown:
            logger.warning(
                f"[document_processor] MarkItDown returned empty markdown for {inp.filename}"
            )

        return DocumentProcessorOutput(
            filename=inp.filename,
            markdown=markdown,
            chunks=1,
            characters=len(markdown),
            mime_type=inp.mime_type,
        )
