# Job Alert Digest

Job Alert Digest is a Gmail-first workflow that collects job alert emails, extracts candidate roles, scores them against Alan's profile with an LLM, and renders a concise digest for review.

## Design

- primary source: Gmail query/label
- extraction: LLM-assisted parsing of job opportunities from email bodies
- ranking: LLM-based fit scoring against a profile document plus configurable preference hints
- output: HTML + text email digest

## Suggested use

- source queries such as `label:"Jobs" newer_than:1d`
- targeting senior data science, analytics, AI, and operational intelligence roles
- maintain the canonical profile in `config/profile/alan_job_profile.md`
- prioritizing relevance over raw job volume
