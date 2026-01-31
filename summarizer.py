"""
AI-powered opinion summarizer.

Uses Claude to generate concise, blog-style summaries of court opinions.
"""

import logging
from typing import Optional

import anthropic

import config
from scraper import Opinion

logger = logging.getLogger(__name__)

# System prompt for generating summaries in the blog style
SUMMARY_SYSTEM_PROMPT = """You are a legal blog writer who summarizes Fourth Circuit Court of Appeals opinions in a concise, accessible style.

Your summaries should:
1. Be 1-3 sentences long
2. Lead with the case name in italics (using *Case Name* format)
3. State the key legal issue or question
4. Explain the court's holding/decision
5. Use plain language accessible to attorneys and legal professionals
6. Be informative but brief

Example summaries in your style:

*Doe v. Fairfax County School Board* - The Fourth Circuit held that a school board's policy requiring students to use bathrooms corresponding to their biological sex did not violate Title IX, finding the policy served legitimate privacy interests.

*United States v. Johnson* - The court affirmed the defendant's conviction for wire fraud, rejecting arguments that the government failed to prove the defendant acted with intent to defraud where evidence showed he knowingly made false statements to investors.

*Smith v. Virginia Department of Corrections* - Reversing the district court's dismissal, the Fourth Circuit found that a prisoner stated a plausible Eighth Amendment claim for deliberate indifference to serious medical needs where prison officials allegedly ignored his requests for treatment over several months.

Write your summary based on the opinion text provided. Focus on what matters most to legal practitioners."""


class OpinionSummarizer:
    """Generates AI-powered summaries of court opinions."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the summarizer.

        Args:
            api_key: Anthropic API key. Defaults to config.ANTHROPIC_API_KEY.
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def summarize(self, opinion: Opinion, opinion_text: str) -> str:
        """
        Generate a summary for a court opinion.

        Args:
            opinion: The Opinion metadata.
            opinion_text: The extracted text from the opinion PDF.

        Returns:
            A 1-3 sentence summary of the opinion.
        """
        logger.info(f"Generating summary for {opinion.case_number}: {opinion.case_name}")

        # Truncate text if too long (Claude can handle a lot, but let's be efficient)
        max_chars = 50000
        if len(opinion_text) > max_chars:
            opinion_text = opinion_text[:max_chars] + "\n\n[Opinion text truncated...]"

        user_prompt = f"""Please summarize the following Fourth Circuit Court of Appeals opinion.

Case Information:
- Case Number: {opinion.case_number}
- Case Name: {opinion.case_name}
- Date Filed: {opinion.date_filed.strftime('%B %d, %Y')}

Opinion Text:
{opinion_text}

Provide a 1-3 sentence summary in the blog style described. Start with the case name in italics."""

        try:
            response = self.client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=300,
                system=SUMMARY_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            summary = response.content[0].text.strip()
            logger.debug(f"Generated summary: {summary[:100]}...")
            return summary

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def summarize_batch(
        self,
        opinions_with_text: list[tuple[Opinion, str]]
    ) -> list[tuple[Opinion, str]]:
        """
        Generate summaries for multiple opinions.

        Args:
            opinions_with_text: List of (Opinion, text) tuples.

        Returns:
            List of (Opinion, summary) tuples.
        """
        results = []

        for opinion, text in opinions_with_text:
            try:
                summary = self.summarize(opinion, text)
                results.append((opinion, summary))
            except Exception as e:
                logger.error(f"Failed to summarize {opinion.case_number}: {e}")
                # Include a fallback summary
                fallback = (
                    f"*{opinion.case_name}* (Case No. {opinion.case_number}) - "
                    f"Summary unavailable. See the full opinion for details."
                )
                results.append((opinion, fallback))

        return results
