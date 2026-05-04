# OpenClaw Cron Setup: Prof G Weekly Insights

## Goal

Run the Prof G weekly email workflow every Saturday afternoon.

## Project directory

```bash
cd "/Users/alangewerc/Library/CloudStorage/GoogleDrive-alangewerc@gmail.com/My Drive/AI & Data Projects/email-workflows"
```

## Workflow command

Use this command for the scheduled weekly run:

```bash
/usr/local/bin/python3.13 -m email_workflow.cli run prof-g-insights
```

Use this command for a test run without sending email:

```bash
/usr/local/bin/python3.13 -m email_workflow.cli run prof-g-insights --skip-delivery
```

## Required environment

The cron environment must include the DeepSeek API key:

```bash
export DEEPSEEK_API_KEY="PASTE_KEY_HERE"
```

Gmail access must also work for the `gog` CLI under the same user:

```bash
gog gmail search "label:newsletter-prof-g newer_than:7d" --account alangewerc@gmail.com --max 1 --json --no-input
```

## Cron entry

Open the crontab:

```bash
crontab -e
```

Add this entry to run every Saturday at 3:00 PM:

```cron
0 15 * * 6 cd "/Users/alangewerc/Library/CloudStorage/GoogleDrive-alangewerc@gmail.com/My Drive/AI & Data Projects/email-workflows" && DEEPSEEK_API_KEY="PASTE_KEY_HERE" /usr/local/bin/python3.13 -m email_workflow.cli run prof-g-insights >> logs/prof-g-insights-cron.log 2>&1
```

If the machine timezone is not `Australia/Perth`, add this timezone line above the cron entry:

```cron
TZ=Australia/Perth
0 15 * * 6 cd "/Users/alangewerc/Library/CloudStorage/GoogleDrive-alangewerc@gmail.com/My Drive/AI & Data Projects/email-workflows" && DEEPSEEK_API_KEY="PASTE_KEY_HERE" /usr/local/bin/python3.13 -m email_workflow.cli run prof-g-insights >> logs/prof-g-insights-cron.log 2>&1
```

## Expected output

Each run creates artifacts under:

```text
runs/prof-g-insights/YYYYMMDD-HHMMSS/
```

The workflow sends an email titled:

```text
Weekly Prof G Insights
```

## Validation

After adding cron, run this manually once:

```bash
cd "/Users/alangewerc/Library/CloudStorage/GoogleDrive-alangewerc@gmail.com/My Drive/AI & Data Projects/email-workflows"
DEEPSEEK_API_KEY="PASTE_KEY_HERE" /usr/local/bin/python3.13 -m email_workflow.cli run prof-g-insights --skip-delivery
```

Then check the cron log:

```bash
tail -n 100 logs/prof-g-insights-cron.log
```
