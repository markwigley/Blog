# Fourth Circuit Court Opinion Email Digest

Automated weekly digest of new published opinions from the Fourth Circuit Court of Appeals.

**Every Friday at 5pm**, this system will:
1. Check for new published opinions on the Fourth Circuit website
2. Download and read each opinion PDF
3. Generate a concise summary using AI (Claude)
4. Email you a digest with all the new opinions

## Quick Start (For Non-Coders)

If you don't have coding experience, follow these steps carefully:

### Step 1: Get Your API Keys

You'll need two things:

**A) Anthropic API Key** (for AI summaries)
1. Go to https://console.anthropic.com/
2. Create an account
3. Go to "API Keys" and create a new key
4. Copy the key (starts with `sk-ant-...`)
5. Note: This costs money per use (~$0.01-0.05 per opinion summary)

**B) Gmail App Password** (for sending emails)
1. Go to https://myaccount.google.com/
2. Click "Security" in the left menu
3. Make sure "2-Step Verification" is ON (turn it on if not)
4. After 2-Step Verification is on, go back to Security
5. Search for "App passwords" or find it under "2-Step Verification"
6. Create a new app password:
   - Select app: "Mail"
   - Select device: "Other" → type "Court Digest"
7. Copy the 16-character password (looks like: `abcd efgh ijkl mnop`)

### Step 2: Deploy to the Cloud (PythonAnywhere - Free Option)

See the **"Cloud Deployment with PythonAnywhere"** section below for step-by-step instructions.

---

## Features

- **Automatic Scraping**: Fetches new published opinions from [ca4.uscourts.gov](https://www.ca4.uscourts.gov/opinions/recent-opinions/published-only)
- **AI-Powered Summaries**: Uses Claude to generate blog-style summaries with case name, date, category, panel, and holding
- **Weekly Email Digest**: Sends formatted HTML emails every Friday at 5pm Eastern
- **Deduplication**: Tracks reviewed opinions to avoid sending duplicates

## Local Setup (For Developers)

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
- `SMTP_USERNAME`: Your Gmail address
- `SMTP_PASSWORD`: Your Gmail App Password (NOT your regular password)
- `EMAIL_FROM`: Your Gmail address

Optional variables:
- `RECIPIENT_EMAIL`: Digest recipient (default: mswigley@wardandsmith.com)
- `SMTP_HOST`: SMTP server (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP port (default: 587)
- `TIMEZONE`: Schedule timezone (default: US/Eastern)

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

## Cloud Deployment with PythonAnywhere

PythonAnywhere is a beginner-friendly cloud platform that can run this script for free.

### Step-by-Step Setup

1. **Create Account**
   - Go to https://www.pythonanywhere.com/
   - Click "Pricing & signup" → "Create a Beginner account" (free)

2. **Upload Files**
   - After logging in, click "Files" in the top menu
   - Click "Upload a file" and upload all the `.py` files and `requirements.txt`
   - Or use the "Open Bash console" and run:
     ```bash
     git clone https://github.com/YOUR_USERNAME/Blog.git
     cd Blog
     ```

3. **Install Dependencies**
   - Click "Consoles" → "Bash" to open a terminal
   - Run:
     ```bash
     pip3 install --user -r requirements.txt
     ```

4. **Create Your .env File**
   - In the Files section, click "Open another file" and type `.env`
   - Paste this content (fill in your actual values):
     ```
     ANTHROPIC_API_KEY=sk-ant-your-key-here
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USERNAME=your.email@gmail.com
     SMTP_PASSWORD=your-16-char-app-password
     EMAIL_FROM=your.email@gmail.com
     RECIPIENT_EMAIL=mswigley@wardandsmith.com
     TIMEZONE=US/Eastern
     ```
   - Click "Save"

5. **Set Up Scheduled Task**
   - Click "Tasks" in the top menu
   - Under "Scheduled tasks", enter:
     - Time: `21:00` (this is 5pm Eastern in UTC)
     - Command: `cd ~/Blog && python3 main.py --run-now`
   - Click "Create"
   - Change the frequency dropdown to "Weekly" and select "Friday"

6. **Test It**
   - Open a Bash console and run:
     ```bash
     cd ~/Blog
     python3 main.py --test-email
     ```
   - Check your email for the test message

### Free Tier Limitations
- PythonAnywhere free tier allows one scheduled task
- The task runs once per day (or weekly if you set it)
- If you need more, their paid tier is ~$5/month

---

## Running Locally as a Service

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

Summaries are generated in a legal blog style matching the Fourth Circuit Appeals Substack format:

> **White v. Warden** (Jan. 13, 2026) (Civil – First Step Act) (NIEMEYER, Wilkinson, King dissenting): In a 2-1 decision, the Court held that prisoner White wasn't entitled to First Step Act time credits for three days spent in a transfer center because he didn't actually participate in any programming during that period—the statute requires earning credits through "successful participation," not mere presence. Judge King dissented, arguing the government waived its participation argument and that the majority's new theory lacked factual support.

Each summary includes:
- **Case name and date**
- **Category** (Civil, Criminal, Admin, Immigration, etc.)
- **Panel** with author in CAPS and dissents noted
- **2-4 sentence summary** of the holding and key reasoning

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
