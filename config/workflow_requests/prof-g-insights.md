# Workflow Request: Prof G Insights

Status: Implemented
Slug: prof-g-insights
Created: 2026-04-30

## What this workflow should do
- Build a weekly, long-form insight report from emails routed to the Prof G Gmail label.
- Focus on relevant strategic, economic, market, business, technology, and cultural insights from the week's Prof G emails.
- Each relevant insight should include a clear conclusion, supporting data/evidence from the source emails, and what else to consider or watch next.

## Trigger or frequency
- Weekly on Saturday afternoon, Perth time.
- Configured schedule anchor: `2026-05-02T15:00:00+08:00`.

## Inputs and data sources
- Gmail account: `alangewerc@gmail.com`.
- Gmail query: `label:newsletter-prof-g newer_than:7d`.
- Max threads: 12.
- Max insights: 5, prioritizing stronger long-form insights over breadth.

## Output and delivery
- Email to `alangewerc@gmail.com`.
- Subject: `Weekly Prof G Insights`.
- Long-form sections, one per insight.
- Each insight section contains:
  - Conclusion.
  - Supporting data / evidence.
  - What to consider / watch next.
  - Source email subjects.

## Rules and constraints
- Use only the supplied Prof G emails as source material.
- Do not invent facts, numbers, claims, or citations.
- Fewer strong insights are better than many weak ones.
- Keep the report detailed; it does not need to be short.

## Notes for Codex implementation
- Implemented as workflow type `prof_g_insights`.
- Prompt file: `config/prompts/prof_g_insights_synthesize.txt`.
- Catalog id: `prof-g-insights`.
