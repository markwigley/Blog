"""
Opinion tracking module.

Keeps track of which opinions have already been reviewed and summarized
to avoid sending duplicate summaries.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from scraper import Opinion

logger = logging.getLogger(__name__)


class OpinionTracker:
    """Tracks which opinions have been reviewed."""

    def __init__(self, storage_file: Optional[Path] = None):
        """
        Initialize the tracker.

        Args:
            storage_file: Path to the JSON file for storing reviewed opinions.
                         Defaults to config.REVIEWED_OPINIONS_FILE.
        """
        self.storage_file = storage_file or config.REVIEWED_OPINIONS_FILE
        self._reviewed: dict[str, dict] = {}
        self._load()

    def _load(self):
        """Load the reviewed opinions from storage."""
        config.ensure_data_dirs()

        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r") as f:
                    self._reviewed = json.load(f)
                logger.info(f"Loaded {len(self._reviewed)} reviewed opinions")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load reviewed opinions: {e}")
                self._reviewed = {}
        else:
            self._reviewed = {}

    def _save(self):
        """Save the reviewed opinions to storage."""
        config.ensure_data_dirs()

        try:
            with open(self.storage_file, "w") as f:
                json.dump(self._reviewed, f, indent=2, default=str)
            logger.debug("Saved reviewed opinions")
        except IOError as e:
            logger.error(f"Failed to save reviewed opinions: {e}")
            raise

    def is_reviewed(self, opinion: Opinion) -> bool:
        """
        Check if an opinion has already been reviewed.

        Args:
            opinion: The Opinion to check.

        Returns:
            True if the opinion has been reviewed, False otherwise.
        """
        return opinion.unique_id in self._reviewed

    def mark_reviewed(self, opinion: Opinion, summary: str):
        """
        Mark an opinion as reviewed.

        Args:
            opinion: The Opinion that was reviewed.
            summary: The generated summary for the opinion.
        """
        self._reviewed[opinion.unique_id] = {
            "case_number": opinion.case_number,
            "case_name": opinion.case_name,
            "date_filed": opinion.date_filed.isoformat(),
            "pdf_url": opinion.pdf_url,
            "summary": summary,
            "reviewed_at": datetime.now().isoformat(),
        }
        self._save()
        logger.info(f"Marked opinion as reviewed: {opinion.case_number}")

    def get_new_opinions(self, opinions: list[Opinion]) -> list[Opinion]:
        """
        Filter a list of opinions to only include new (unreviewed) ones.

        Args:
            opinions: List of Opinion objects to filter.

        Returns:
            List of opinions that have not been reviewed.
        """
        new_opinions = [op for op in opinions if not self.is_reviewed(op)]
        logger.info(f"Found {len(new_opinions)} new opinions out of {len(opinions)}")
        return new_opinions

    def get_all_reviewed(self) -> dict[str, dict]:
        """Get all reviewed opinions."""
        return self._reviewed.copy()

    def clear(self):
        """Clear all reviewed opinions (useful for testing)."""
        self._reviewed = {}
        self._save()
        logger.info("Cleared all reviewed opinions")
