from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
}


@dataclass(
    frozen=True
)
class ParsedPage:
    page_number: int | None
    text: str


@dataclass(
    frozen=True
)
class ParsedDocument:
    filename: str
    content_type: str | None
    pages: list[ParsedPage]

    @property
    def full_text(
        self,
    ) -> str:
        return "\n\n".join(
            page.text
            for page in self.pages
            if page.text.strip()
        )


class DocumentParser:

    @staticmethod
    def _normalize_filename(
        filename: str,
    ) -> str:
        return Path(
            filename
        ).name

    def parse(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> ParsedDocument:

        safe_filename = (
            self._normalize_filename(
                filename
            )
        )

        extension = (
            Path(
                safe_filename
            )
            .suffix
            .lower()
        )

        if (
            extension
            not in SUPPORTED_EXTENSIONS
        ):
            raise ValueError(
                "Unsupported document type. "
                "Supported formats are PDF, TXT and Markdown."
            )

        if not content:
            raise ValueError(
                "Uploaded document is empty."
            )

        if extension == ".pdf":
            return self._parse_pdf(
                filename=safe_filename,
                content=content,
                content_type=content_type,
            )

        return self._parse_text(
            filename=safe_filename,
            content=content,
            content_type=content_type,
        )

    def _parse_pdf(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> ParsedDocument:

        try:
            reader = PdfReader(
                BytesIO(
                    content
                )
            )

        except Exception as exc:
            raise ValueError(
                "Unable to read the PDF document."
            ) from exc

        pages: list[
            ParsedPage
        ] = []

        for page_index, page in enumerate(
            reader.pages,
            start=1,
        ):
            try:
                text = (
                    page.extract_text()
                    or ""
                )

            except Exception:
                text = ""

            text = (
                text.strip()
            )

            if not text:
                continue

            pages.append(
                ParsedPage(
                    page_number=page_index,
                    text=text,
                )
            )

        if not pages:
            raise ValueError(
                "No readable text was found in the PDF. "
                "Scanned/image-only PDFs require OCR support."
            )

        return ParsedDocument(
            filename=filename,
            content_type=(
                content_type
                or "application/pdf"
            ),
            pages=pages,
        )

    def _parse_text(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> ParsedDocument:

        text = None

        for encoding in (
            "utf-8",
            "utf-8-sig",
            "latin-1",
        ):
            try:
                text = content.decode(
                    encoding
                )

                break

            except UnicodeDecodeError:
                continue

        if text is None:
            raise ValueError(
                "Unable to decode the document text."
            )

        text = (
            text.strip()
        )

        if not text:
            raise ValueError(
                "The document does not contain readable text."
            )

        return ParsedDocument(
            filename=filename,
            content_type=content_type,
            pages=[
                ParsedPage(
                    page_number=None,
                    text=text,
                )
            ],
        )


document_parser = (
    DocumentParser()
)