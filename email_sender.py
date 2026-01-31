"""
Email sending module.

Sends the weekly digest of court opinion summaries via email.
"""

import logging
import re
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
            "FOURTH CIRCUIT COURT OF APPEALS",
            f"Weekly Opinion Digest - {date_str}",
            "",
            f"This week's digest includes {len(opinions_with_summaries)} new published opinion(s).",
            "",
            "=" * 60,
            "",
        ]

        for opinion, summary in opinions_with_summaries:
            lines.extend([
                summary,
                "",
                f"PDF: {opinion.pdf_url}",
                "",
                "-" * 60,
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
            "body { font-family: Georgia, serif; max-width: 750px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.6; }",
            "h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; font-size: 1.5em; }",
            ".intro { color: #555; margin-bottom: 25px; }",
            ".opinion { margin: 25px 0; padding-bottom: 25px; border-bottom: 1px solid #ddd; }",
            ".opinion:last-of-type { border-bottom: none; }",
            ".case-header { font-weight: bold; color: #1a365d; }",
            ".case-meta { color: #666; }",
            ".panel { font-size: 0.95em; }",
            ".panel .author { text-transform: uppercase; }",
            ".summary-text { margin-top: 8px; }",
            ".pdf-link { margin-top: 10px; font-size: 0.9em; }",
            "a { color: #2c5282; }",
            ".footer { margin-top: 40px; padding-top: 20px; border-top: 2px solid #1a365d; font-size: 0.85em; color: #666; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Fourth Circuit Weekly Digest</h1>",
            f'<p class="intro"><strong>{date_str}</strong> &mdash; {len(opinions_with_summaries)} new published opinion(s) this week.</p>',
        ]

        for opinion, summary in opinions_with_summaries:
            # The summary already contains case name, date, category, panel, and text
            # Format it nicely for HTML display
            html_summary = self._format_summary_html(summary, opinion.pdf_url)
            html_parts.append(html_summary)

        html_parts.extend([
            '<div class="footer">',
            '<p>This is an automated digest. Summaries are AI-generated and should be '
            'verified against the full opinions for accuracy.</p>',
            '<p>Source: <a href="https://www.ca4.uscourts.gov/opinions/recent-opinions/published-only">'
            'Fourth Circuit Court of Appeals - Recent Published Opinions</a></p>',
            '</div>',
            '</body>',
            '</html>',
        ])

        return "\n".join(html_parts)

    def _format_summary_html(self, summary: str, pdf_url: str) -> str:
        """Format a summary for HTML display."""
        # Try to parse the structured summary format:
        # Case Name (Date) (Category) (Panel): Summary text
        pattern = r'^(.+?)\s*\(([^)]+)\)\s*\(([^)]+)\)\s*\(([^)]+)\):\s*(.+)$'
        match = re.match(pattern, summary, re.DOTALL)

        if match:
            case_name, date, category, panel, text = match.groups()
            return f'''<div class="opinion">
<p><span class="case-header">{case_name.strip()}</span> <span class="case-meta">({date.strip()}) ({category.strip()})</span> <span class="panel">({panel.strip()})</span></p>
<p class="summary-text">{text.strip()}</p>
<p class="pdf-link"><a href="{pdf_url}">View Full Opinion (PDF)</a></p>
</div>'''
        else:
            # Fallback: just display the summary as-is
            return f'''<div class="opinion">
<p>{summary}</p>
<p class="pdf-link"><a href="{pdf_url}">View Full Opinion (PDF)</a></p>
</div>'''


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

        date_str = datetime.now().strftime('%b. %d, %Y').replace('May.', 'May')
        test_summary = (
            f"Test v. Configuration ({date_str}) (Civil – Test Case) "
            f"(EXAMPLE, Judge, Panel): This is a test email to verify that the "
            f"Fourth Circuit Opinion Digest email system is properly configured. "
            f"If you received this email, your setup is working correctly."
        )

        return sender.send_digest([(test_opinion, test_summary)], recipient)

    except Exception as e:
        logger.error(f"Test email failed: {e}")
        return False
