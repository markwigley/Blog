# Fourth Circuit Court Opinion Email Digest

Automated weekly digest of new published opinions from the Fourth Circuit Court of Appeals.

## Features

- **Automatic Scraping**: Fetches new published opinions from [ca4.uscourts.gov](https://www.ca4.uscourts.gov/opinions/recent-opinions/published-only)
- **AI-Powered Summaries**: Uses Claude to generate 1-3 sentence summaries in a legal blog style
- **Weekly Email Digest**: Sends formatted HTML emails every Friday at 5pm
- **Deduplication**: Tracks reviewed opinions to avoid sending duplicates

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude
- `SMTP_USERNAME`: Email account username
- `SMTP_PASSWORD`: Email account password (use app-specific password for Gmail)
- `EMAIL_FROM`: Sender email address

Optional variables:
- `RECIPIENT_EMAIL`: Digest recipient (default: mswigley@wardandsmith.com)
- `SMTP_HOST`: SMTP server (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP port (default: 587)
- `TIMEZONE`: Schedule timezone (default: US/Eastern)

### 3. Gmail Setup (if using Gmail)

1. Enable 2-factor authentication on your Google account
2. Generate an App Password: Google Account → Security → App Passwords
3. Use the App Password as `SMTP_PASSWORD`

## Usage

### Start the Scheduler

Run continuously, executing every Friday at 5pm:

```bash
python main.py
```

### Run Immediately

Process opinions and send digest now:

```bash
python main.py --run-now
```

### Test Email Configuration

Send a test email to verify setup:

```bash
python main.py --test-email
```

### Override Recipient

```bash
python main.py --run-now --recipient someone@example.com
```

## File Structure

```
Blog/
├── main.py              # Entry point and CLI
├── config.py            # Configuration settings
├── scraper.py           # Fourth Circuit website scraper
├── pdf_extractor.py     # PDF text extraction
├── summarizer.py        # AI summary generation
├── email_sender.py      # Email sending
├── tracker.py           # Opinion tracking (deduplication)
├── scheduler.py         # Friday 5pm scheduler
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
├── .env                 # Your configuration (not in git)
└── data/
    ├── reviewed_opinions.json   # Tracking data
    └── opinion_pdfs/            # PDF cache
```

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/court-digest.service`:

```ini
[Unit]
Description=Fourth Circuit Opinion Digest
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Blog
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable court-digest
sudo systemctl start court-digest
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## Summary Style

Summaries are generated in a legal blog style, for example:

> *Smith v. Virginia Department of Corrections* - Reversing the district court's dismissal, the Fourth Circuit found that a prisoner stated a plausible Eighth Amendment claim for deliberate indifference to serious medical needs where prison officials allegedly ignored his requests for treatment over several months.

## Troubleshooting

### No opinions found
- The court website structure may have changed
- Check network connectivity
- Review logs in `digest.log`

### Email not sending
- Verify SMTP credentials
- For Gmail, ensure you're using an App Password
- Check spam folder

### PDF extraction failing
- Some PDFs may be scanned images (OCR not supported)
- Very large opinions are truncated to first 30 pages

## License

MIT
