"""
Scraper for Fourth Circuit Court of Appeals opinions.

Fetches the list of recent published opinions from ca4.uscourts.gov.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


@dataclass
class Opinion:
    """Represents a Fourth Circuit Court opinion."""
    case_number: str
    case_name: str
    date_filed: datetime
    pdf_url: str
    judge: Optional[str] = None

    @property
    def unique_id(self) -> str:
        """Generate a unique identifier for tracking purposes."""
        return f"{self.case_number}_{self.date_filed.strftime('%Y%m%d')}"

    def __hash__(self):
        return hash(self.unique_id)

    def __eq__(self, other):
        if isinstance(other, Opinion):
            return self.unique_id == other.unique_id
        return False


class FourthCircuitScraper:
    """Scraper for Fourth Circuit Court of Appeals opinions."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def fetch_recent_opinions(self) -> list[Opinion]:
        """
        Fetch the list of recent published opinions from the Fourth Circuit.

        Returns:
            List of Opinion objects.
        """
        logger.info(f"Fetching opinions from {config.OPINIONS_URL}")

        try:
            response = self.session.get(
                config.OPINIONS_URL,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch opinions page: {e}")
            raise

        return self._parse_opinions_page(response.text)

    def _parse_opinions_page(self, html: str) -> list[Opinion]:
        """
        Parse the HTML page to extract opinion information.

        The Fourth Circuit opinions page typically contains a table with columns:
        - Case Number
        - Case Name (with link to PDF)
        - Date Filed
        - Judge/Panel
        """
        soup = BeautifulSoup(html, "lxml")
        opinions = []

        # Try to find the opinions table - the structure may vary
        # Look for tables with opinion data
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                opinion = self._parse_table_row(row)
                if opinion:
                    opinions.append(opinion)

        # If no tables found, try alternative parsing (div-based layout)
        if not opinions:
            opinions = self._parse_div_layout(soup)

        # Also try to find links to PDFs directly
        if not opinions:
            opinions = self._parse_pdf_links(soup)

        logger.info(f"Found {len(opinions)} opinions")
        return opinions

    def _parse_table_row(self, row) -> Optional[Opinion]:
        """Parse a table row to extract opinion data."""
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            return None

        try:
            # Extract case number (usually first column)
            case_number = cells[0].get_text(strip=True)

            # Extract case name and PDF link (usually second column)
            case_name_cell = cells[1]
            link = case_name_cell.find("a", href=True)

            if not link:
                return None

            case_name = link.get_text(strip=True)
            pdf_url = link["href"]

            # Make URL absolute if relative
            if not pdf_url.startswith("http"):
                pdf_url = urljoin(config.FOURTH_CIRCUIT_BASE_URL, pdf_url)

            # Extract date (usually third column)
            date_str = cells[2].get_text(strip=True)
            date_filed = self._parse_date(date_str)

            # Extract judge if available (fourth column)
            judge = None
            if len(cells) > 3:
                judge = cells[3].get_text(strip=True)

            return Opinion(
                case_number=case_number,
                case_name=case_name,
                date_filed=date_filed,
                pdf_url=pdf_url,
                judge=judge
            )
        except (IndexError, ValueError) as e:
            logger.debug(f"Failed to parse row: {e}")
            return None

    def _parse_div_layout(self, soup: BeautifulSoup) -> list[Opinion]:
        """Parse opinions from a div-based layout."""
        opinions = []

        # Look for common opinion container patterns
        containers = soup.find_all(["div", "article"], class_=re.compile(
            r"opinion|case|entry|item", re.IGNORECASE
        ))

        for container in containers:
            link = container.find("a", href=re.compile(r"\.pdf$", re.IGNORECASE))
            if not link:
                continue

            case_name = link.get_text(strip=True)
            pdf_url = link["href"]

            if not pdf_url.startswith("http"):
                pdf_url = urljoin(config.FOURTH_CIRCUIT_BASE_URL, pdf_url)

            # Try to find case number
            case_number = self._extract_case_number(container.get_text())

            # Try to find date
            date_text = container.get_text()
            date_filed = self._extract_date_from_text(date_text)

            if case_name and pdf_url:
                opinions.append(Opinion(
                    case_number=case_number or "Unknown",
                    case_name=case_name,
                    date_filed=date_filed or datetime.now(),
                    pdf_url=pdf_url
                ))

        return opinions

    def _parse_pdf_links(self, soup: BeautifulSoup) -> list[Opinion]:
        """Parse opinions by finding all PDF links."""
        opinions = []

        # Find all links to PDFs
        pdf_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.IGNORECASE))

        for link in pdf_links:
            href = link["href"]
            case_name = link.get_text(strip=True)

            # Skip if no meaningful text
            if not case_name or len(case_name) < 5:
                continue

            if not href.startswith("http"):
                href = urljoin(config.FOURTH_CIRCUIT_BASE_URL, href)

            # Try to extract case number from URL or text
            case_number = self._extract_case_number_from_url(href)
            if not case_number:
                case_number = self._extract_case_number(case_name)

            opinions.append(Opinion(
                case_number=case_number or "Unknown",
                case_name=case_name,
                date_filed=datetime.now(),  # Default to now if date not found
                pdf_url=href
            ))

        return opinions

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats."""
        date_formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%y",
        ]

        date_str = date_str.strip()

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Default to current date if parsing fails
        logger.warning(f"Could not parse date: {date_str}")
        return datetime.now()

    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Try to extract a date from text."""
        # Common date patterns
        patterns = [
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{1,2}-\d{1,2}-\d{4})",
            r"(\w+ \d{1,2}, \d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._parse_date(match.group(1))

        return None

    def _extract_case_number(self, text: str) -> Optional[str]:
        """Extract a case number from text."""
        # Fourth Circuit case number patterns: XX-XXXX, XX-XXXXX
        patterns = [
            r"(\d{2}-\d{4,5})",
            r"No\.\s*(\d{2}-\d{4,5})",
            r"Case\s*#?\s*(\d{2}-\d{4,5})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_case_number_from_url(self, url: str) -> Optional[str]:
        """Extract case number from PDF URL."""
        # URLs often contain the case number
        match = re.search(r"(\d{2}-\d{4,5})", url)
        if match:
            return match.group(1)
        return None

    def download_pdf(self, opinion: Opinion) -> bytes:
        """
        Download the PDF for an opinion.

        Args:
            opinion: The Opinion object with the PDF URL.

        Returns:
            The PDF content as bytes.
        """
        logger.info(f"Downloading PDF: {opinion.pdf_url}")

        try:
            response = self.session.get(
                opinion.pdf_url,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error(f"Failed to download PDF: {e}")
            raise
