Migrate Weekly Economy Sensemaking into email-workflow
Work inside the existing project already open in this Codex project chat:

/Users/alangewerc/Library/CloudStorage/GoogleDrive-alangewerc@gmail.com/My Drive/AI & Data Projects/email-workflows

This is not a new project. This is a migration/addition to the existing email-workflow platform.

Goal
Migrate the existing Weekly Economy Sensemaking email into the new workflow system as a proper first-class workflow.

This new workflow should become part of the platform in the same way the Citizen Brief workflow already lives there.
Existing reference to migrate
There is an existing OpenClaw cron job called:

Weekly Economy Sensemaking email

It currently:
reviews the previous 7 days of macro/economics content
focuses especially on Gmail label Newsletter/Business.Economics
prioritises Westpac content
uses linked webpages and PDFs where useful
creates both Markdown and HTML
saves archive files to Google Drive
emails the result to alangewerc@gmail.com

Please use the existing cron definition and current surrounding context as the behavioral reference.

Product intent
This workflow should produce a weekly macro/economy briefing that is:
concise
insightful
signal-focused
grounded in both narrative and market context

It should not be a generic news summary or a stock-picking report.

The point is to give Alan a strong weekly sense of:
the macro direction
the most important developments
why they matter
what to watch next

New required feature: market snapshot at the top
At the start of the email, include a market snapshot section.
This should show selected commodities/indexes/markets with performance over:
last 7 days
last 30 days
last 365 days

Suggested instruments include:
iron ore
gold
Brent crude
copper
ASX 200
Nasdaq
S&P 500
AUD/USD

It is fine to make the exact tracked set configurable.
This market snapshot should come before the narrative sections.

Key design requirement: Gmail label is the primary source
The economy workflow should follow the same architectural idea as Citizen Brief:

primary source = Gmail emails gathered via configured Gmail search query / label
secondary enrichment = selective linked webpages and PDFs

The workflow should not be designed first around general web crawling.
It should start from Alan’s Gmail content.

Use config-driven Gmail queries such as:
label:"Newsletter/Business.Economics" newer_than:7d

and allow prioritization settings such as:
preferred senders like Westpac
Source model
Design the workflow around this content pipeline:

gather relevant economy emails from Gmail
parse email bodies
selectively extract links / PDFs from those emails
fetch readable text from selected webpages
fetch/extract text from selected PDFs where worthwhile
combine all of that into normalized source material
synthesize into the weekly brief
render HTML + Markdown/text
archive + email

Important: link/PDF handling should be selective
Do not parse every possible link or PDF.

Use pragmatic rules such as:
prioritize known high-value senders (especially Westpac)
prioritize substantive report/outlook/research links
limit links/PDFs per email
gracefully fall back if extraction fails
keep token/input volume under control

The design should be robust, not brittle.

Output structure
The weekly email should roughly follow this shape:

Market Snapshot
tracked instruments
current/latest value if available
7d / 30d / 365d change

Conclusion
short direct summary first

Main Points
most important developments of the week

Why It Matters
practical significance / macro significance

What I’m Watching Next
key forward-looking items

Optionally:
a short note when a view is primarily Westpac’s framing vs the workflow’s own synthesis

Archival requirement
Preserve the archival behavior.
The workflow should save both Markdown and HTML outputs to:

/Users/alangewerc/Library/CloudStorage/GoogleDrive-alangewerc@gmail.com/My Drive/Finance/Economy Reports/{YEAR}/

with filenames like:

{DATE} - Weekly Economy Sensemaking.md
{DATE} - Weekly Economy Sensemaking.html

Use Australia/Perth timezone and YYYY-MM-DD date format.

Delivery requirement
Send the email to:

alangewerc@gmail.com

with subject exactly:
Weekly Economy Sensemaking

HTML first, with plain text/markdown fallback if needed.

Configurability
Do not hardcode important behavior deep in Python if it can reasonably live in config.

The workflow should support configurable settings for things like:
Gmail query / label source
preferred senders (e.g. Westpac)
source extraction limits
tracked market instruments
time horizons (7d / 30d / 365d)
archive path
email subject
prompt file locations
section names if useful
Prompt/instruction management
Any prompts used for:
source evaluation
economy summarization
final editorial synthesis

should be externalized into prompt files where appropriate, consistent with the current project patterns.

The workflow should also fit the existing web app/admin surface approach so prompts/config can be more easily inspected/edited later.

Platform integration
Integrate this cleanly into the existing email-workflow platform:
workflow registry
workflow runner
CLI
config examples
docs
tests
web app visibility

Suggested workflow id
Use something like:

weekly_economy_sensemaking

or another clean equivalent.

Validation requirements
Before replying, run and report meaningful validation, including at least:

python -m email_workflow.cli list
python -m email_workflow.cli run <workflow_id> --dry-run
relevant tests
any import checks needed
If this repo is intended to run from .venv, use the project’s actual working environment consistently.

Quality bar
fit naturally into the architecture already present
preserve the spirit of the current cron workflow
make Gmail label sourcing explicit
handle PDF/link enrichment cleanly
include the market snapshot section at the top
produce something that feels migration-ready, not hacky

Response format
When done, return exactly these sections:

What I added
How the weekly economy workflow works
How Gmail, links, and PDFs are handled
How the market snapshot works
Config/files added or updated
Validation results
Remaining limitations
Recommended next steps