from __future__ import annotations

from app.core import BaseAgent
from logger import logger

from .models import DocumentProcessorInput, DocumentProcessorOutput
from langchain_docling.loader import DoclingLoader, ExportType


class DocumentProcessorAgent(BaseAgent):
    """
    Converts uploaded incident evidence into markdown using Docling.

    Docling supports PDF, DOCX, PPTX, HTML, and other office/document formats.
    The markdown output is designed to be passed into downstream LLM agents.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("document_processor", **kwargs)

    async def run(self, inp: DocumentProcessorInput) -> DocumentProcessorOutput:
        self._log(f"Converting document filename={inp.filename}")

        loader = DoclingLoader(
            file_path=inp.file_path,
            export_type=ExportType.MARKDOWN,
        )

        docs = list(loader.lazy_load())
        markdown_parts: list[str] = []

        for index, doc in enumerate(docs, start=1):
            content = getattr(doc, "page_content", "") or ""
            if content.strip():
                markdown_parts.append(
                    f"<!-- chunk:{index} source:{inp.filename} -->\n{content.strip()}"
                )

        markdown = "\n\n".join(markdown_parts).strip()

        if not markdown:
            logger.warning(
                f"[document_processor] Docling returned empty markdown for {inp.filename}"
            )

        return DocumentProcessorOutput(
            filename=inp.filename,
            markdown=markdown,
            chunks=len(docs),
            characters=len(markdown),
            mime_type=inp.mime_type,
        )
