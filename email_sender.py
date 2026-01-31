"""
Email sending module.

Sends the weekly digest of court opinion summaries via email.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import config
from scraper import Opinion

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends email digests of court opinion summaries."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        """
        Initialize the email sender.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            username: SMTP username.
            password: SMTP password.
            from_email: Sender email address.
        """
        self.smtp_host = smtp_host or config.SMTP_HOST
        self.smtp_port = smtp_port or config.SMTP_PORT
        self.username = username or config.SMTP_USERNAME
        self.password = password or config.SMTP_PASSWORD
        self.from_email = from_email or config.EMAIL_FROM

        if not all([self.smtp_host, self.username, self.password, self.from_email]):
            raise ValueError(
                "Email configuration incomplete. "
                "Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_FROM."
            )

    def send_digest(
        self,
        opinions_with_summaries: list[tuple[Opinion, str]],
        recipient: Optional[str] = None,
    ) -> bool:
        """
        Send the weekly digest email.

        Args:
            opinions_with_summaries: List of (Opinion, summary) tuples.
            recipient: Email recipient. Defaults to config.RECIPIENT_EMAIL.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        recipient = recipient or config.RECIPIENT_EMAIL

        if not opinions_with_summaries:
            logger.info("No new opinions to send")
            return True

        logger.info(
            f"Sending digest with {len(opinions_with_summaries)} opinions to {recipient}"
        )

        # Build the email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._build_subject(len(opinions_with_summaries))
        msg["From"] = self.from_email
        msg["To"] = recipient

        # Create plain text and HTML versions
        text_content = self._build_text_body(opinions_with_summaries)
        html_content = self._build_html_body(opinions_with_summaries)

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info("Digest email sent successfully")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _build_subject(self, count: int) -> str:
        """Build the email subject line."""
        date_str = datetime.now().strftime("%B %d, %Y")
        opinion_word = "Opinion" if count == 1 else "Opinions"
        return f"Fourth Circuit Weekly Digest: {count} New {opinion_word} - {date_str}"

    def _build_text_body(
        self,
        opinions_with_summaries: list[tuple[Opinion, str]]
    ) -> str:
        """Build the plain text email body."""
        date_str = datetime.now().strftime("%B %d, %Y")

        lines = [
            f"FOURTH CIRCUIT COURT OF APPEALS",
            f"Weekly Opinion Digest - {date_str}",
            "",
            f"This week's digest includes {len(opinions_with_summaries)} new published opinion(s).",
            "",
            "=" * 60,
            "",
        ]

        for opinion, summary in opinions_with_summaries:
            lines.extend([
                f"Case: {opinion.case_name}",
                f"No.: {opinion.case_number}",
                f"Filed: {opinion.date_filed.strftime('%B %d, %Y')}",
                f"PDF: {opinion.pdf_url}",
                "",
                summary,
                "",
                "-" * 40,
                "",
            ])

        lines.extend([
            "",
            "This is an automated digest. Summaries are AI-generated and should be",
            "verified against the full opinions for accuracy.",
            "",
            "Source: https://www.ca4.uscourts.gov/opinions/recent-opinions/published-only",
        ])

        return "\n".join(lines)

    def _build_html_body(
        self,
        opinions_with_summaries: list[tuple[Opinion, str]]
    ) -> str:
        """Build the HTML email body."""
        date_str = datetime.now().strftime("%B %d, %Y")

        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<style>",
            "body { font-family: Georgia, serif; max-width: 700px; margin: 0 auto; padding: 20px; color: #333; }",
            "h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; }",
            "h2 { color: #2c5282; font-size: 1.1em; margin-top: 0; }",
            ".opinion { background: #f7fafc; border-left: 4px solid #2c5282; padding: 15px; margin: 20px 0; }",
            ".meta { font-size: 0.9em; color: #666; margin-bottom: 10px; }",
            ".summary { line-height: 1.6; }",
            ".summary em { font-style: italic; }",
            "a { color: #2c5282; }",
            ".footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.85em; color: #666; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Fourth Circuit Weekly Digest</h1>",
            f"<p><strong>{date_str}</strong> - {len(opinions_with_summaries)} new published opinion(s)</p>",
        ]

        for opinion, summary in opinions_with_summaries:
            # Convert markdown-style italics to HTML
            html_summary = summary.replace("*", "<em>", 1).replace("*", "</em>", 1)

            html_parts.extend([
                '<div class="opinion">',
                f'<h2>{opinion.case_name}</h2>',
                '<div class="meta">',
                f'Case No. {opinion.case_number} | ',
                f'Filed: {opinion.date_filed.strftime("%B %d, %Y")} | ',
                f'<a href="{opinion.pdf_url}">View Full Opinion (PDF)</a>',
                '</div>',
                f'<div class="summary">{html_summary}</div>',
                '</div>',
            ])

        html_parts.extend([
            '<div class="footer">',
            '<p>This is an automated digest. Summaries are AI-generated and should be '
            'verified against the full opinions for accuracy.</p>',
            '<p>Source: <a href="https://www.ca4.uscourts.gov/opinions/recent-opinions/published-only">'
            'Fourth Circuit Court of Appeals</a></p>',
            '</div>',
            '</body>',
            '</html>',
        ])

        return "\n".join(html_parts)


def send_test_email(recipient: str) -> bool:
    """
    Send a test email to verify configuration.

    Args:
        recipient: Email address to send test to.

    Returns:
        True if successful, False otherwise.
    """
    try:
        sender = EmailSender()

        # Create a test opinion
        test_opinion = Opinion(
            case_number="24-1234",
            case_name="Test v. Configuration",
            date_filed=datetime.now(),
            pdf_url="https://www.ca4.uscourts.gov/test.pdf",
        )

        test_summary = (
            "*Test v. Configuration* - This is a test email to verify that the "
            "Fourth Circuit Opinion Digest email system is properly configured."
        )

        return sender.send_digest([(test_opinion, test_summary)], recipient)

    except Exception as e:
        logger.error(f"Test email failed: {e}")
        return False
