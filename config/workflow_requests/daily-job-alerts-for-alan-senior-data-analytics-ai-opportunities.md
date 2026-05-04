Work inside the existing email-workflow project already open in this Codex project chat.

This is not a new project. This is a migration/addition to the existing workflow platform.

Goal
Create a new workflow that turns Alan’s incoming job alert emails into a structured, useful Job Alert digest inside the email-workflow system.

This should become a first-class workflow in the platform, similar in spirit to Citizen Brief and the new economy workflow.

Core requirement: source from Gmail label/query
This workflow should follow the same architectural pattern as the other email workflows:
primary source = Gmail emails
gathered through configured Gmail queries / labels
not built first around generic scraping

The main idea is:
Alan already receives job-related emails in Gmail.
This workflow should collect those emails from the right label/query, parse them, extract useful job postings, assess fit, and produce a digest.

Source design
Use Gmail as the primary source via config-driven search query.

For example, support configuration like:
label:"job.alert" newer_than:1d
or label:"Jobs" newer_than:1d
or another configurable Gmail query

The exact query should be configurable, not hardcoded.
Product intent
The purpose of this workflow is to help Alan quickly spot high-fit opportunities without drowning in low-quality job alert noise.

The workflow should optimize for:
relevance
clarity
signal over volume
decision usefulness

It should not just forward raw job alert content.

User context / fit criteria
Alan is especially interested in roles related to:
data science
analytics
AI
machine learning
principal / lead / head-of-function-lite roles
digital / decision science / operational intelligence roles
mining / energy / resources / operations / regulated industries
roles with strong business impact
roles that still keep some technical depth

Good examples include:
Principal Data Scientist
Principal Analytics roles
Senior AI roles
Lead data / AI / analytics roles
Head of Data / Analytics / AI (where still reasonably hands-on)
operational analytics / intelligence roles

This targeting should be configurable and evolvable, not buried permanently in code.

Workflow behavior
The workflow should roughly do this:

gather job-related emails from Gmail via configured query
parse and extract individual job opportunities from those emails
normalize useful fields where possible:
role title
company
location
link
summary/description snippet
source email
assess fit/relevance
rank or group opportunities
produce an email digest
expose config/prompts/docs/webapp visibility

Job extraction design
Be pragmatic.

Job emails may contain:
one clear role
many roles in one email
noisy newsletter-like formatting
links out to job pages

A good first pass is:
extract as much structured information as reasonably possible from the email body
optionally follow links when necessary and worthwhile
avoid building something fragile or overcomplicated

The workflow should be designed so extraction can improve later.

Relevance / ranking
The digest should rank or filter roles based on fit.
Support configurable factors such as:
inclusion keywords
exclusion keywords
target seniority
target functions
target industries
target geographies / remote preferences
preferred signals like “principal”, “lead”, “analytics”, “AI”, “data science”, etc.

It is fine if first-pass ranking is a mix of:
rules-based filtering
optional LLM scoring/summarization

Output structure
The digest should be clean and decision-oriented.

Suggested structure:
Top Matches
strongest opportunities first
short explanation of why they fit

Worth a Look
medium-fit opportunities

Maybe / Lower Fit (optional)
only if useful and not noisy

For each role, include as much of this as available:
title
company
location
short summary
why it may be relevant
link to role
Prompt/instruction management
Any prompts used for:
job relevance scoring
extraction cleanup
summarization
editorial ranking

should be externalized into prompt files consistent with the existing project pattern.

This workflow should fit the web app/admin model so prompts and config can be inspected and edited later.

Configurability
Do not hardcode everything into Python.

Support configurable settings for things like:
Gmail query / label
inclusion keywords
exclusion keywords
industries
locations
seniority preferences
digest size / max number of jobs
prompt file references
email subject

Suggested workflow id
Use something like:

job_alert_digest

or

job_emails_digest
Delivery
The workflow should support dry-run and render cleanly inside the platform.

It should produce:
HTML email
text fallback

Send to:
alangewerc@gmail.com

Use a sensible subject, e.g.:
Job Alert Digest

Make the exact subject configurable.

Platform integration
Integrate this cleanly into the existing email-workflow platform:
workflow registry
runner
CLI
config examples
docs
tests
web app visibility

Validation requirements
Before replying, run and report meaningful validation, including at least:

python -m email_workflow.cli list
python -m email_workflow.cli run <workflow_id> --dry-run
relevant tests
import checks if needed

If the repo expects .venv, use the project’s actual working environment consistently.
Quality bar
source from Gmail label/query explicitly
fit naturally into the current architecture
produce a useful digest, not raw forwarding
optimize for relevance over volume
keep it extensible and not brittle
feel migration-ready

Response format
When done, return exactly these sections:

What I added
How the job alert workflow works
How Gmail sourcing and extraction work
How ranking/relevance works
Config/files added or updated
Validation results
Remaining limitations
Recommended next steps