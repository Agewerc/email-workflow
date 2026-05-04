"""Job alert digest workflow."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.renderers import render_digest_html, render_digest_text
from email_workflow.schemas import (
    ContentItem,
    JobAlertDigestWorkflowConfig,
    JobOpportunity,
    RenderedEmail,
    SectionContent,
    WorkflowContent,
    WorkflowMeta,
)
from email_workflow.utils.files import resolve_project_path
from email_workflow.workflows.base import BaseWorkflow


TITLE_MIN_WORDS = 2
TITLE_MAX_CHARS = 90
MALFORMED_TITLE_PREFIXES = (
    "*",
    "-",
    "•",
    "apply",
    "click",
    "high-impact",
    "meaningful work",
    "opportunity to",
)
LOCATION_HINTS = ("perth", "wa", "australia", "remote", "hybrid", "sydney", "melbourne", "brisbane")
JOB_URL_PATTERN = re.compile(r"https?://[^\s\]]+/(?:comm/jobs/view|job)/[^\s\]]*", re.I)


class JobAlertDigestWorkflow(BaseWorkflow):
    workflow_type = "job_alert_digest"

    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        return WorkflowMeta(
            id=ctx.definition.id,
            name=ctx.definition.name,
            description=ctx.definition.description,
            tags=ctx.definition.tags,
        )

    def config(self, ctx: WorkflowContext) -> JobAlertDigestWorkflowConfig:
        return JobAlertDigestWorkflowConfig.model_validate({"workflow_type": self.workflow_type, **ctx.definition.config})

    def _prompt_path(self, ctx: WorkflowContext, key: str) -> Path:
        config = self.config(ctx)
        return resolve_project_path(config.prompt_files[key])

    def _read_prompt(self, ctx: WorkflowContext, key: str) -> str:
        return self._prompt_path(ctx, key).read_text(encoding="utf-8").strip()

    def _read_profile(self, ctx: WorkflowContext) -> str:
        config = self.config(ctx)
        return resolve_project_path(config.profile_file).read_text(encoding="utf-8").strip()

    def _extract_json_block(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                decoder = json.JSONDecoder()
                _, end = decoder.raw_decode(stripped)
                return stripped[:end]
            except json.JSONDecodeError:
                pass
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                _, end = decoder.raw_decode(text[index:])
                return text[index : index + end]
            except json.JSONDecodeError:
                continue
        return "[]"

    def _clean_text_field(self, value: object) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)
        return text.strip(" \t\r\n*•-")

    def _is_plausible_job(self, job: JobOpportunity) -> bool:
        title = job.title.strip()
        title_lower = title.lower()
        if len(title) < 8 or len(title) > TITLE_MAX_CHARS:
            return False
        if len(title.split()) < TITLE_MIN_WORDS:
            return False
        if "\n" in title or "\r" in title:
            return False
        if any(title_lower.startswith(prefix) for prefix in MALFORMED_TITLE_PREFIXES):
            return False
        if title.count("*") or title.count("•"):
            return False
        if re.search(r"\$\d|level\s+\d|superannuation|\bsuper\b", title_lower):
            return False
        if not re.search(r"[a-zA-Z]", title):
            return False
        return True

    def _dedupe_jobs(self, jobs: list[JobOpportunity]) -> list[JobOpportunity]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[JobOpportunity] = []
        for job in jobs:
            key = (
                re.sub(r"\W+", " ", job.title.lower()).strip(),
                re.sub(r"\W+", " ", job.company.lower()).strip(),
                re.sub(r"\W+", " ", job.location.lower()).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(job)
        return deduped

    def _shortlist_jobs(self, jobs: list[JobOpportunity], config: JobAlertDigestWorkflowConfig) -> list[JobOpportunity]:
        shortlisted = [job for job in jobs if job.score >= config.min_digest_score]
        if shortlisted:
            return shortlisted[: config.max_digest_jobs]

        plausible = [job for job in jobs if job.score >= max(35, config.min_digest_score - 20)]
        if plausible:
            return plausible[: min(3, config.max_digest_jobs)]
        return []

    def _normalize_llm_score(self, raw_score: object) -> int:
        score = int(raw_score or 0)
        if 0 <= score <= 5:
            return {0: 0, 1: 10, 2: 25, 3: 45, 4: 70, 5: 90}[score]
        return max(0, min(score, 100))

    def _normalize_rule_score(self, raw_score: int) -> int:
        if raw_score <= 0:
            return 0
        if raw_score <= 5:
            return {1: 10, 2: 20, 3: 35, 4: 50, 5: 75}[raw_score]
        return min(95, 75 + ((raw_score - 5) * 5))

    def _line_is_noise(self, line: str) -> bool:
        normalized = line.strip().lower()
        if not normalized:
            return True
        noise_fragments = (
            "logo",
            "featured",
            "view job",
            "company alumni",
            "actively hiring",
            "new jobs match",
            "results from",
            "saved search",
            "tracking=",
            "otpToken",
            "seekcdn.com",
            "bx-branding-gateway",
            "linkedin.com",
            "unsubscribe",
        )
        if any(fragment.lower() in normalized for fragment in noise_fragments):
            return True
        return normalized.startswith("[http") or normalized.startswith("http")

    def _looks_like_location(self, line: str) -> bool:
        normalized = line.lower()
        return any(hint in normalized for hint in LOCATION_HINTS) or bool(re.fullmatch(r"\d{4}", line.strip()))

    def _candidate_from_lines(
        self,
        lines: list[str],
        link: str,
        source_email: str,
        item: ContentItem,
    ) -> JobOpportunity | None:
        useful = [self._clean_text_field(line) for line in lines if not self._line_is_noise(line)]
        useful = [line for line in useful if line]
        if len(useful) < 2:
            return None

        location = ""
        location_index: int | None = None
        for index in range(len(useful) - 1, -1, -1):
            if self._looks_like_location(useful[index]):
                location = useful[index]
                location_index = index
                break

        if location_index is not None and location_index >= 2:
            title = useful[location_index - 2]
            company = useful[location_index - 1]
        else:
            title = useful[-2]
            company = useful[-1]

        opportunity = JobOpportunity(
            title=title,
            company=company,
            location=location,
            link=link,
            summary=f"{title} at {company}{f' in {location}' if location else ''}.",
            source_email=source_email,
            metadata={"email_sender": item.source, "email_id": item.identifier, "extractor": "structured_fallback"},
        )
        if not self._is_plausible_job(opportunity):
            return None
        return opportunity

    def _extract_structured_jobs_from_item(self, item: ContentItem, max_jobs: int) -> list[JobOpportunity]:
        raw_lines = (item.body or item.summary).splitlines()
        lines = [line.strip() for line in raw_lines]
        jobs: list[JobOpportunity] = []

        for index, line in enumerate(lines):
            match = JOB_URL_PATTERN.search(line)
            if not match:
                continue
            candidate = self._candidate_from_lines(lines[max(0, index - 8) : index], match.group(0), item.title, item)
            if candidate is not None:
                jobs.append(candidate)
            if len(jobs) >= max_jobs:
                break
        return self._dedupe_jobs(jobs)

    def _extract_jobs_from_item(self, ctx: WorkflowContext, item: ContentItem) -> list[JobOpportunity]:
        config = self.config(ctx)
        prompt = self._read_prompt(ctx, "extract").format(
            max_jobs_per_email=config.max_jobs_per_email,
            subject=item.title,
            sender=item.source,
            date=item.published_at,
            content=(item.body or item.summary)[: config.body_max_chars],
        )
        response = ctx.llm_provider.complete(prompt, config)
        payload = self._extract_json_block(response.text)
        parsed = json.loads(payload)
        if not isinstance(parsed, list):
            return []
        jobs: list[JobOpportunity] = []
        for job in parsed[: config.max_jobs_per_email]:
            if not isinstance(job, dict) or not job.get("title"):
                continue
            opportunity = JobOpportunity(
                title=self._clean_text_field(job.get("title")),
                company=self._clean_text_field(job.get("company")),
                location=self._clean_text_field(job.get("location")),
                link=self._clean_text_field(job.get("link")),
                summary=self._clean_text_field(job.get("summary")),
                source_email=item.title,
                metadata={"email_sender": item.source, "email_id": item.identifier},
            )
            if self._is_plausible_job(opportunity):
                jobs.append(opportunity)
        if not jobs:
            jobs = self._extract_structured_jobs_from_item(item, config.max_jobs_per_email)
        return jobs

    def _score_job(self, job: JobOpportunity, config: JobAlertDigestWorkflowConfig) -> tuple[int, list[str]]:
        haystack = " ".join(
            [
                job.title,
                job.company,
                job.location,
                job.summary,
            ]
        ).lower()
        score = 0
        reasons: list[str] = []

        for keyword in config.seniority_keywords:
            if keyword.lower() in haystack:
                score += 3
                reasons.append(f"seniority match: {keyword}")

        for keyword in config.inclusion_keywords:
            if keyword.lower() in haystack:
                score += 2
                reasons.append(f"target keyword: {keyword}")

        for keyword in config.target_functions:
            if keyword.lower() in haystack:
                score += 2
                reasons.append(f"target function: {keyword}")

        for keyword in config.target_industries:
            if keyword.lower() in haystack:
                score += 1
                reasons.append(f"industry fit: {keyword}")

        for keyword in config.target_locations:
            if keyword.lower() in haystack:
                score += 1
                reasons.append(f"location fit: {keyword}")

        for keyword in config.exclusion_keywords:
            if keyword.lower() in haystack:
                score -= 4
                reasons.append(f"exclusion keyword: {keyword}")

        if not reasons:
            reasons.append("limited direct fit signals found")
        return score, reasons

    def _format_jobs_for_scoring(self, jobs: list[JobOpportunity]) -> str:
        lines: list[str] = []
        for index, job in enumerate(jobs, start=1):
            lines.append(
                "\n".join(
                    [
                        f"--- Job {index} ---",
                        f"Title: {job.title}",
                        f"Company: {job.company or 'Unknown'}",
                        f"Location: {job.location or 'Unknown'}",
                        f"Summary: {job.summary or 'No summary extracted.'}",
                        f"Link: {job.link or 'No direct link extracted.'}",
                        f"Source email: {job.source_email or 'Unknown'}",
                    ]
                )
            )
        return "\n\n".join(lines)

    def _llm_score_jobs(self, ctx: WorkflowContext, jobs: list[JobOpportunity]) -> list[tuple[int, str]]:
        config = self.config(ctx)
        prompt = self._read_prompt(ctx, "score").format(
            profile=self._read_profile(ctx),
            jobs_to_score=self._format_jobs_for_scoring(jobs),
            target_functions=", ".join(config.target_functions) or "Not specified",
            target_industries=", ".join(config.target_industries) or "Not specified",
            target_locations=", ".join(config.target_locations) or "Not specified",
            inclusion_keywords=", ".join(config.inclusion_keywords) or "Not specified",
            exclusion_keywords=", ".join(config.exclusion_keywords) or "Not specified",
            seniority_keywords=", ".join(config.seniority_keywords) or "Not specified",
        )
        response = ctx.llm_provider.complete(prompt, config)
        payload = self._extract_json_block(response.text)
        parsed = json.loads(payload)
        if not isinstance(parsed, list):
            raise ValueError("LLM job score response was not a JSON array")
        if len(parsed) != len(jobs):
            raise ValueError("LLM job score response length did not match jobs length")
        results: list[tuple[int, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                raise ValueError("LLM job score response contained a non-object item")
            score = self._normalize_llm_score(item.get("score", 0))
            rationale = str(item.get("rationale", "")).strip()
            if not rationale:
                rationale = "AI fit score returned without a rationale."
            results.append((score, rationale))
        return results

    def _format_jobs_for_editor(self, jobs: list[JobOpportunity]) -> str:
        lines: list[str] = []
        for index, job in enumerate(jobs, start=1):
            lines.append(
                "\n".join(
                    [
                        f"--- Job {index} ---",
                        f"Title: {job.title}",
                        f"Company: {job.company}",
                        f"Location: {job.location}",
                        f"Score: {job.score}",
                        f"Why it may fit: {job.relevance_reason}",
                        f"Summary: {job.summary}",
                        f"Link: {job.link}",
                        f"Source email: {job.source_email}",
                    ]
                )
            )
        return "\n\n".join(lines)

    def _fallback_section_summary(self, jobs: list[JobOpportunity]) -> str:
        if not jobs:
            return "NO_STRONG_ITEMS"
        bullets: list[str] = []
        for job in jobs:
            reason = job.relevance_reason or "Possible fit based on extracted details."
            bullets.append(
                f"- **{job.title}** — {job.company} ({job.location or 'Location not specified'})\n"
                f"  Why it may fit: {reason}\n"
                f"  Link: {job.link}"
            )
        return "\n\n".join(bullets)

    def _parse_editor_output(self, text: str, section_names: list[str]) -> dict[str, str]:
        parsed: dict[str, str] = {}
        current: str | None = None
        buffer: list[str] = []
        normalized_names = {name.lower(): name for name in section_names}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            line = re.sub(r"^#+\s*", "", line)
            if line.startswith("**") and line.endswith("**") and len(line) > 4:
                line = line[2:-2].strip()
            canonical = normalized_names.get(line.lower())
            if canonical is not None:
                if current is not None:
                    parsed[current] = "\n".join(buffer).strip() or "NO_STRONG_ITEMS"
                current = canonical
                buffer = []
                continue
            if current is not None:
                buffer.append(raw_line)
        if current is not None:
            parsed[current] = "\n".join(buffer).strip() or "NO_STRONG_ITEMS"
        for name in section_names:
            parsed.setdefault(name, "NO_STRONG_ITEMS")
        return parsed

    def gather(self, ctx: WorkflowContext) -> WorkflowContent:
        config = self.config(ctx)
        section = ctx.gmail_provider.gather_section(
            "Job Alerts",
            config.gmail_query,
            config.max_threads,
            config.email_account,
            config.body_max_chars,
        )
        content = WorkflowContent(sections=[section])
        artifact = ctx.artifact_path("sources.json")
        artifact.write_text(content.model_dump_json(indent=2), encoding="utf-8")
        ctx.artifacts["sources"] = artifact
        return content

    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        config = self.config(ctx)
        section = gathered.sections[0] if gathered.sections else SectionContent(name="Job Alerts", items=[])
        jobs: list[JobOpportunity] = []

        for item in section.items:
            extracted = self._extract_jobs_from_item(ctx, item)
            jobs.extend(extracted)
        jobs = self._dedupe_jobs(jobs)

        if jobs:
            try:
                scored_jobs = self._llm_score_jobs(ctx, jobs)
                for job, (score, rationale) in zip(jobs, scored_jobs, strict=False):
                    job.score = score
                    job.relevance_reason = rationale
            except Exception:
                if not config.llm_score_fallback_to_rules:
                    raise
                for job in jobs:
                    score, reasons = self._score_job(job, config)
                    job.score = self._normalize_rule_score(score)
                    job.relevance_reason = f"Fallback rules score. {'; '.join(reasons[:3])}"

        jobs.sort(key=lambda job: job.score, reverse=True)
        candidates_artifact = ctx.artifact_path("candidates.json")
        candidates_artifact.write_text(
            json.dumps([job.model_dump(mode="json") for job in jobs], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["candidates"] = candidates_artifact

        shortlisted = self._shortlist_jobs(jobs, config)

        jobs_artifact = ctx.artifact_path("jobs.json")
        jobs_artifact.write_text(
            json.dumps([job.model_dump(mode="json") for job in shortlisted], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["jobs"] = jobs_artifact

        section_names = ["Top Matches", "Worth a Look", "Maybe / Lower Fit"]
        if not shortlisted:
            final_sections = [SectionContent(name=name, summary="NO_STRONG_ITEMS") for name in section_names]
            return WorkflowContent(sections=final_sections, metadata={"jobs": []})

        editor_prompt = self._read_prompt(ctx, "editor").format(
            max_digest_jobs=config.max_digest_jobs,
            ranked_jobs=self._format_jobs_for_editor(shortlisted),
        )
        try:
            response = ctx.llm_provider.complete(editor_prompt, config)
            final_text = response.text.strip()
            parsed = self._parse_editor_output(final_text, section_names)
            editor_artifact = ctx.artifact_path("editor.txt")
            editor_artifact.write_text(final_text, encoding="utf-8")
            ctx.artifacts["editor"] = editor_artifact
            if all(value == "NO_STRONG_ITEMS" for value in parsed.values()):
                raise ValueError("Editor returned no usable shortlist summaries")
            final_sections = [SectionContent(name=name, summary=parsed[name]) for name in section_names]
        except Exception:
            top_jobs = [job for job in shortlisted if job.score >= max(70, config.min_digest_score + 15)]
            worth_jobs = [job for job in shortlisted if job not in top_jobs]
            final_sections = [
                SectionContent(name="Top Matches", summary=self._fallback_section_summary(top_jobs)),
                SectionContent(name="Worth a Look", summary=self._fallback_section_summary(worth_jobs)),
                SectionContent(name="Maybe / Lower Fit", summary="NO_STRONG_ITEMS"),
            ]
        summaries_artifact = ctx.artifact_path("summaries.json")
        summaries_artifact.write_text(
            json.dumps({section.name: section.summary for section in final_sections}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["summaries"] = summaries_artifact
        return WorkflowContent(
            sections=final_sections,
            metadata={"jobs": [job.model_dump(mode="json") for job in shortlisted]},
        )

    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        config = self.config(ctx)
        date_label = datetime.now().strftime("%A, %d %B %Y")
        html = render_digest_html(
            resolve_project_path(config.template_html),
            subject=config.email_subject,
            heading="Job Alert Digest",
            date_label=date_label,
            footer_label="Generated by Email Workflow Platform",
            sections=content.sections,
        )
        text = render_digest_text(
            resolve_project_path(config.template_text),
            subject=config.email_subject,
            date_label=date_label,
            footer_label="Generated by Email Workflow Platform",
            sections=content.sections,
        )
        html_artifact = ctx.artifact_path("email.html")
        html_artifact.write_text(html, encoding="utf-8")
        text_artifact = ctx.artifact_path("email.txt")
        text_artifact.write_text(text, encoding="utf-8")
        ctx.artifacts["email_html"] = html_artifact
        ctx.artifacts["email_text"] = text_artifact
        return RenderedEmail(subject=config.email_subject, html=html, text=text)
