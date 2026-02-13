#!/usr/bin/env python3
"""
Fourth Circuit Court of Appeals Opinion Digest

Main entry point for the weekly email digest system.

This program:
1. Scrapes new published opinions from the Fourth Circuit website
2. Extracts text from opinion PDFs
3. Generates AI-powered summaries using Claude
4. Emails a digest to the configured recipient
5. Runs automatically every Friday at 5pm

Usage:
    python main.py              # Start the scheduler (runs every Friday at 5pm)
    python main.py --run-now    # Run the digest immediately
    python main.py --test-email # Send a test email to verify configuration
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta

import config
from email_sender import EmailSender, send_test_email
from pdf_extractor import PDFExtractor
from scheduler import DigestScheduler
from scraper import FourthCircuitScraper, Opinion
from summarizer import OpinionSummarizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("digest.log"),
    ]
)
logger = logging.getLogger(__name__)


def run_digest() -> bool:
    """
    Run the full digest workflow.

    1. Fetch recent opinions from the Fourth Circuit
    2. Filter to only new (unreviewed) opinions
    3. Download and extract text from each opinion PDF
    4. Generate AI summaries
    5. Send email digest
    6. Mark opinions as reviewed

    Returns:
        True if successful, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("Starting Fourth Circuit Opinion Digest")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        # Initialize components
        scraper = FourthCircuitScraper()
        extractor = PDFExtractor()
        summarizer = OpinionSummarizer()
        emailer = EmailSender()

        # Step 1: Fetch recent opinions
        logger.info("Step 1: Fetching recent opinions...")
        all_opinions = scraper.fetch_recent_opinions()
        logger.info(f"Found {len(all_opinions)} total opinions on the page")

        if not all_opinions:
            logger.warning("No opinions found on the website")
            return True

        # Step 2: Filter to only opinions from the last 7 days
        logger.info("Step 2: Filtering to opinions from the last 7 days...")
        cutoff_date = datetime.now() - timedelta(days=7)
        new_opinions = [op for op in all_opinions if op.date_filed >= cutoff_date]

        if not new_opinions:
            logger.info("No opinions from the last 7 days")
            return True

        logger.info(f"Found {len(new_opinions)} opinions from the last 7 days")

        # Step 3: Process each opinion
        logger.info("Step 3: Downloading and extracting opinion text...")
        opinions_with_summaries: list[tuple[Opinion, str]] = []

        for i, opinion in enumerate(new_opinions, 1):
            logger.info(f"Processing opinion {i}/{len(new_opinions)}: {opinion.case_number}")

            try:
                # Download PDF
                pdf_content = scraper.download_pdf(opinion)

                # Extract text
                opinion_text = extractor.extract_text(pdf_content)

                if not opinion_text or len(opinion_text) < 100:
                    logger.warning(f"Could not extract meaningful text from {opinion.case_number}")
                    opinion_text = f"Case: {opinion.case_name}\nCase Number: {opinion.case_number}"

                # Generate summary
                logger.info(f"Step 4: Generating summary for {opinion.case_number}...")
                summary = summarizer.summarize(opinion, opinion_text)

                opinions_with_summaries.append((opinion, summary))
                logger.info(f"Summary generated for {opinion.case_number}")

            except Exception as e:
                logger.error(f"Error processing {opinion.case_number}: {e}")
                fallback = (
                    f"{opinion.case_name} (Case No. {opinion.case_number}) - "
                    f"Summary unavailable due to processing error."
                )
                opinions_with_summaries.append((opinion, fallback))

        # Step 5: Send email
        logger.info("Step 5: Sending email digest...")
        success = emailer.send_digest(opinions_with_summaries)

        if success:
            logger.info("=" * 60)
            logger.info("Digest completed successfully!")
            logger.info(f"Sent {len(opinions_with_summaries)} opinion summaries")
            logger.info("=" * 60)
            return True
        else:
            logger.error("Failed to send email digest")
            return False

    except Exception as e:
        logger.exception(f"Digest failed with error: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fourth Circuit Court of Appeals Opinion Digest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Start the scheduler (runs every Friday at 5pm)
  python main.py --run-now    Run the digest immediately
  python main.py --test-email Send a test email to verify configuration

Environment Variables:
  ANTHROPIC_API_KEY    Required for AI summaries
  SMTP_HOST           SMTP server (default: smtp.gmail.com)
  SMTP_PORT           SMTP port (default: 587)
  SMTP_USERNAME       SMTP login username
  SMTP_PASSWORD       SMTP login password
  EMAIL_FROM          Sender email address
  RECIPIENT_EMAIL     Digest recipient (default: mswigley@wardandsmith.com)
  TIMEZONE            Schedule timezone (default: US/Eastern)
        """
    )

    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the digest immediately instead of waiting for schedule"
    )

    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send a test email to verify email configuration"
    )

    parser.add_argument(
        "--recipient",
        type=str,
        default=None,
        help="Override recipient email"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (debug) logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Ensure data directories exist
    config.ensure_data_dirs()

    if args.test_email:
        logger.info(f"Sending test email to {args.recipient}...")
        if send_test_email(args.recipient):
            logger.info("Test email sent successfully!")
            sys.exit(0)
        else:
            logger.error("Test email failed")
            sys.exit(1)

    if args.run_now:
        logger.info("Running digest now...")
        success = run_digest()
        sys.exit(0 if success else 1)

    # Start the scheduler
    logger.info("Starting Fourth Circuit Opinion Digest Scheduler")
    logger.info(f"Schedule: Every {config.SCHEDULE_DAY.capitalize()} at {config.SCHEDULE_TIME}")
    logger.info(f"Timezone: {config.TIMEZONE}")
    logger.info(f"Recipients: {', '.join(config.RECIPIENT_EMAILS)}")

    scheduler = DigestScheduler(run_digest)
    scheduler.start()

    next_run = scheduler.get_next_run_time()
    if next_run:
        logger.info(f"Next scheduled run: {next_run}")

    # Keep running
    scheduler.run_forever()


if __name__ == "__main__":
    main()
