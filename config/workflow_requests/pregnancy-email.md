# Workflow Request: Pregnancy Week-by-Week Email

Status: Draft
Slug: pregnancy-weekly
Created: 2026-05-02

## What this workflow should do
- Send a warm, factual weekly email about the baby's current stage of development.
- Focus on what is happening during the current gestational week: growth, organs/senses, movement, size, and major milestones.
- Include a short partner-focused section with useful ways to support the pregnancy that week.
- Keep the tone calm, positive, and non-alarming.

## Trigger or frequency
- Weekly on Monday morning, Perth time.
- The workflow should calculate the current pregnancy week from one configured anchor:
  - Estimated due date, preferred.
  - Or first day of last menstrual period, if due date is not available.
- Stop automatically after week 41 unless explicitly extended.

## Inputs and data sources
- Recipient: `alangewerc@gmail.com`.
- Pregnancy anchor: provisional estimated due date `2026-11-15`.
- Implied LMP estimate from that due date: `2026-02-08`.
- The due date is expected to be adjustable as scans/medical guidance refine it.
- Timezone: `Australia/Perth`.
- Primary evidence sources:
  - ACOG patient FAQ: "How Your Fetus Grows During Pregnancy".
  - Mayo Clinic fetal development week-by-week pages.
  - NHS week-by-week pregnancy guide.
  - Better Health Channel Australia pregnancy week-by-week guide.
- Optional personal context:
  - Baby nickname.
  - Partner name.
  - Known appointment dates or scan dates.
  - Preferred tone: practical, emotional, detailed, concise.

## Output and delivery
- Email to `alangewerc@gmail.com`.
- Subject format: `Pregnancy week {{ week }}: {{ short_milestone }}`.
- Suggested sections:
  - `This week at a glance`: one concise paragraph.
  - `Baby development`: 3-5 bullets about what is changing.
  - `Approximate size`: only if supported by source data for that week.
  - `What mum may notice`: gentle, general information; avoid diagnosis.
  - `How I can support`: 2-4 practical partner actions.
  - `Upcoming things to ask the doctor/midwife`: optional questions, not instructions.
  - `Sources`: links to the pages used.

## Rules and constraints
- Educational only; do not present the email as medical advice.
- Do not diagnose symptoms or suggest treatment decisions.
- Include a short safety line when mentioning symptoms: contact a doctor/midwife for concerning, severe, or unusual symptoms.
- Do not invent measurements, milestones, or medical claims.
- Use gestational age language clearly: pregnancy weeks are normally counted from the first day of the last menstrual period.
- If source pages disagree on exact size or milestone timing, use cautious language such as "around this stage" or omit the claim.
- Avoid fear-heavy content unless the week naturally involves routine testing or a safety topic.

## Notes for Codex implementation
- Implement as a mostly static evidence-backed workflow rather than live web scraping.
- Store week-by-week source facts in a checked-in structured file so emails are deterministic and citeable.
- Store the estimated due date in workflow configuration, not code, so it can be changed later.
- With the provisional due date `2026-11-15`, the first Monday email after this request, `2026-05-04`, should generate approximately week 12 content.
- The LLM can rewrite and personalize the email, but it should only use facts from the structured weekly data.
- Add tests for:
  - due-date-to-week calculation;
  - Monday schedule behavior;
  - stopping after week 41;
  - source citation presence;
  - no email generation when pregnancy anchor is missing.
