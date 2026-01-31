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
SUMMARY_SYSTEM_PROMPT = """You are a legal blog writer who summarizes Fourth Circuit Court of Appeals opinions in an accessible, conversational style for attorneys.

FORMAT YOUR SUMMARY EXACTLY LIKE THIS:
Case Name (Mon. DD, YYYY) (Category) (AUTHOR, OtherJudge, ThirdJudge [note any dissent]): Summary text here.

FORMATTING RULES:
1. Case name in bold (no italics)
2. Date in abbreviated month format: (Jan. 13, 2026)
3. Category tag like: (Civil – Employment), (Criminal – Sentencing), (Admin – Black Lung Benefits Act), (Civil – First Step Act), (Civil – Election Law), (Immigration), (Civil – Section 1983), etc.
4. Panel: Put the opinion AUTHOR in ALL CAPS, other judges in normal case. Note dissents like "King dissenting" or "2-1 decision"
5. Summary: 2-4 sentences explaining what happened, the holding, and key reasoning. Use a conversational tone.

EXAMPLE SUMMARIES IN YOUR STYLE:

White v. Warden (Jan. 13, 2026) (Civil – First Step Act) (NIEMEYER, Wilkinson, King dissenting): In a 2-1 decision, the Court held that prisoner White wasn't entitled to First Step Act time credits for three days spent in a transfer center because he didn't actually participate in any programming during that period—the statute requires earning credits through "successful participation," not mere presence. Judge King dissented, arguing the government waived its participation argument and that the majority's new theory lacked factual support and conflicted with BOP policies awarding credits based on "earning status."

Figueroa v. Butterball, LLC (Jan. 14, 2026) (Civil – Employment) (BENJAMIN, Richardson, Rushing): A turkey loader challenged his employer's wage practices under the Fair Labor Standards Act and the North Carolina Wage and Hour Act. The Fourth Circuit affirmed summary judgment for Butterball, finding no genuine dispute in the record that Figueroa was a piece-rate employee (not hourly) based on his signed offer letter stating he'd be paid "a load rate of $10.80." The Court then went on to hold that Butterball had properly calculated overtime under FLSA regulations for piece-rate workers and rejected Figueroa's claims that hours were improperly shifted between workweeks.

Clinchfield v. DOWCP (Jan. 15, 2026) (Admin – Black Lung Benefits Act) (GREGORY, Wilkinson, Berner): A coal company challenged an award under the Black Lung Benefits Act, arguing that pulmonary function tests used to support the finding were invalid due to minor deviations from regulatory standards. The Fourth Circuit denied the company's petition, emphasizing that PFT quality standards go to evidentiary weight rather than categorical admissibility, and deferred to the ALJ's credibility determinations in this "battle of the experts."

Dominion Coal v. DOWCP (Jan. 15, 2026) (Admin – Black Lung Benefits Act) (DIAZ, Wynn, Harris): Another black lung case. Here, the Fourth Circuit denied Dominion's petition and held that the Department of Labor's Benefits Review Board properly remanded when the ALJ failed to adequately evaluate conflicting expert evidence about CT scans showing pneumoconiosis. The Court also rejected Dominion's constitutional challenge to the ALJ's removal protections, following the Court's K & R Contractors v. Keene from a few years ago in holding that vacatur requires showing the removal provision caused actual harm (which Dominion hadn't shown).

Public Interest Legal Foundation, Inc. v. Wooten (Jan. 16, 2026) (Civil – Election Law) (BERNER, Diaz, Wynn): Third party plaintiff Public Interest Legal Foundation brought this case under the National Voter Registration Act of 1993 after South Carolina refused to disclose its voter registration list. Defendants brought an Article III standing challenge on appeal. Although it noted that two sister circuits had held that PILF lacked standing in functionally identical cases, it punted the standing issue back down for the district court to first develop a record on it.

IMPORTANT INSTRUCTIONS:
- Extract the panel/judges from the opinion text (usually listed at the top)
- Identify the opinion author (their name appears with "writing for the court" or the opinion text starts with their name)
- Determine the legal category based on the subject matter
- Write in a conversational but professional tone—you can use phrases like "punted the issue back down" or note when something is particularly interesting
- If there's a dissent, explain briefly what the dissenter argued
- Focus on what practitioners need to know: what was the issue, what did the court hold, and why"""


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

        # Format date as abbreviated month
        date_str = opinion.date_filed.strftime('%b. %d, %Y').replace('May.', 'May')

        user_prompt = f"""Please summarize the following Fourth Circuit Court of Appeals opinion.

Case Information:
- Case Number: {opinion.case_number}
- Case Name: {opinion.case_name}
- Date Published: {date_str}

IMPORTANT: Use EXACTLY this date in your summary: {date_str}
Do NOT use any other date found in the opinion text. The date parenthetical must be ({date_str}).

Opinion Text:
{opinion_text}

Generate a summary following the exact format described in your instructions. Make sure to:
1. Extract the panel of judges from the opinion (look for "Before" followed by judge names, or judges listed at the top)
2. Identify who wrote the opinion (look for the judge's name at the start of the opinion text or "J., writing")
3. Determine the appropriate legal category
4. Note any dissents or concurrences
5. Write 2-4 sentences summarizing the case in a conversational tone"""

        try:
            response = self.client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=500,
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
                date_str = opinion.date_filed.strftime('%b. %d, %Y').replace('May.', 'May')
                fallback = (
                    f"{opinion.case_name} ({date_str}) (Category Unknown) (Panel Unknown): "
                    f"Summary unavailable due to processing error. See the full opinion for details."
                )
                results.append((opinion, fallback))

        return results
