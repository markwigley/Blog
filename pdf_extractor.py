"""
PDF text extraction module.

Extracts text content from court opinion PDFs for summarization.
"""

import io
import logging
from pathlib import Path
from typing import Optional

import pdfplumber

import config
from scraper import Opinion

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text from PDF documents."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the PDF extractor.

        Args:
            cache_dir: Directory to cache downloaded PDFs.
                      Defaults to config.OPINIONS_CACHE_DIR.
        """
        self.cache_dir = cache_dir or config.OPINIONS_CACHE_DIR
        config.ensure_data_dirs()

    def extract_text(self, pdf_content: bytes, max_pages: int = 30) -> str:
        """
        Extract text from PDF content.

        Args:
            pdf_content: The PDF file content as bytes.
            max_pages: Maximum number of pages to extract (to limit processing time).

        Returns:
            Extracted text from the PDF.
        """
        try:
            pdf_file = io.BytesIO(pdf_content)

            with pdfplumber.open(pdf_file) as pdf:
                text_parts = []
                pages_to_process = min(len(pdf.pages), max_pages)

                for i, page in enumerate(pdf.pages[:pages_to_process]):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                if len(pdf.pages) > max_pages:
                    logger.info(
                        f"PDF has {len(pdf.pages)} pages, "
                        f"only extracted first {max_pages}"
                    )

                full_text = "\n\n".join(text_parts)
                logger.debug(f"Extracted {len(full_text)} characters from PDF")
                return full_text

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise

    def extract_key_sections(self, text: str) -> dict[str, str]:
        """
        Extract key sections from opinion text.

        Court opinions typically have:
        - Case caption (parties, case number)
        - Syllabus or summary
        - Opinion text
        - Holding/conclusion

        Args:
            text: The full opinion text.

        Returns:
            Dictionary with extracted sections.
        """
        sections = {
            "caption": "",
            "syllabus": "",
            "opinion": "",
            "conclusion": "",
        }

        # The first ~500 chars usually contain the caption
        sections["caption"] = text[:500] if len(text) > 500 else text

        # Look for syllabus section
        syllabus_markers = ["SYLLABUS", "SUMMARY", "HEADNOTE"]
        for marker in syllabus_markers:
            if marker in text.upper():
                idx = text.upper().find(marker)
                # Extract ~2000 chars after the marker
                sections["syllabus"] = text[idx:idx + 2000]
                break

        # Look for conclusion section
        conclusion_markers = ["CONCLUSION", "AFFIRMED", "REVERSED", "REMANDED", "HOLDING"]
        for marker in conclusion_markers:
            if marker in text.upper():
                idx = text.upper().rfind(marker)  # Last occurrence
                sections["conclusion"] = text[max(0, idx - 200):idx + 500]
                break

        # The main opinion is the bulk of the text
        sections["opinion"] = text

        return sections

    def get_first_n_chars(self, text: str, n: int = 15000) -> str:
        """
        Get the first N characters of text, useful for API limits.

        Args:
            text: The full text.
            n: Number of characters to return.

        Returns:
            Truncated text.
        """
        if len(text) <= n:
            return text

        # Try to break at a sentence boundary
        truncated = text[:n]
        last_period = truncated.rfind(".")
        if last_period > n * 0.8:  # Only if we're not losing too much
            truncated = truncated[:last_period + 1]

        return truncated + "\n\n[Text truncated for processing...]"
