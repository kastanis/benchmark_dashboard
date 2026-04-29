#!/usr/bin/env python3
"""Research helper for the benchmark dashboard.

The script intentionally keeps review in the loop. AI mode can draft entries,
but the dashboard is only updated by passing a JSON file to `add`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "benchmarks.json"
SCORES_FILE = ROOT / "data" / "model_scores.json"
SCORE_SOURCES_FILE = ROOT / "data" / "score_sources.json"
TABLEBENCH_HISTORY_FILE = ROOT / "data" / "tablebench_history.json"
INBOX = ROOT / "research_inbox"


REQUIRED_FIELDS = {
    "id",
    "name",
    "category",
    "status",
    "year",
    "journalism_relevance",
    "difficulty",
    "capabilities",
    "why_it_matters",
    "task_shape",
    "signals",
    "source",
}


SCHEMA_HINT = {
    "id": "lowercase-dash-id",
    "name": "Benchmark name",
    "category": "Web research | Tables | Charts | Factuality | Analysis code | Documents | Other",
    "status": "Active | Established | Watchlist",
    "year": 2026,
    "journalism_relevance": 1,
    "difficulty": "Low | Medium | Hard | Very hard",
    "capabilities": ["short tag"],
    "why_it_matters": "One sentence about newsroom relevance.",
    "task_shape": "What the benchmark asks models to do.",
    "signals": ["One strength.", "One caveat."],
    "source": {"label": "Canonical source label", "url": "https://..."},
}


SCORE_REQUIRED_FIELDS = {
    "benchmark_id",
    "benchmark",
    "provider",
    "model",
    "score",
    "metric",
    "higher_is_better",
    "reported_date",
    "source_type",
    "source",
    "note",
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "benchmark"


def load_dashboard() -> dict:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_scores() -> dict:
    with SCORES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_scores(data: dict) -> None:
    data["updated"] = date.today().isoformat()
    with SCORES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_score_sources() -> dict:
    with SCORE_SOURCES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_dashboard(data: dict) -> None:
    data["updated"] = date.today().isoformat()
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validate_entry(entry: dict) -> list[str]:
    errors = []
    missing = REQUIRED_FIELDS - set(entry)
    if missing:
        errors.append(f"Missing fields: {', '.join(sorted(missing))}")
    if not isinstance(entry.get("journalism_relevance"), int) or not 1 <= entry.get("journalism_relevance", 0) <= 5:
        errors.append("journalism_relevance must be an integer from 1 to 5")
    if not isinstance(entry.get("capabilities"), list) or not entry.get("capabilities"):
        errors.append("capabilities must be a non-empty list")
    if not isinstance(entry.get("signals"), list) or len(entry.get("signals", [])) < 2:
        errors.append("signals must include at least two notes")
    source = entry.get("source", {})
    if not isinstance(source, dict) or not source.get("url") or not source.get("label"):
        errors.append("source must include label and url")
    return errors


def validate_score(score: dict) -> list[str]:
    errors = []
    missing = SCORE_REQUIRED_FIELDS - set(score)
    if missing:
        errors.append(f"Missing score fields: {', '.join(sorted(missing))}")
    if not isinstance(score.get("score"), int | float):
        errors.append("score must be numeric")
    source = score.get("source", {})
    if not isinstance(source, dict) or not source.get("url") or not source.get("label"):
        errors.append("source must include label and url")
    return errors


def score_key(score: dict) -> tuple[str, str, str, str]:
    return (
        score["benchmark_id"].lower(),
        score["provider"].lower(),
        score["model"].lower(),
        score["metric"].lower(),
    )


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "benchmark-dashboard-research-agent/0.1 (+local personal research)",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def textify_html(raw: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_score_from_html_row(raw: str, aliases: list[str], score_index: int | None = None) -> float | None:
    rows = re.findall(r"<tr\b[^>]*>.*?</tr>", raw, flags=re.IGNORECASE | re.DOTALL)
    for row in rows:
        if not any(re.search(re.escape(alias), row, flags=re.IGNORECASE) for alias in aliases):
            continue
        bold_values = re.findall(r"<b>\s*(\d{1,3}(?:\.\d+)?)\s*</b>", row, flags=re.IGNORECASE)
        if bold_values:
            return float(bold_values[-1])

        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        numeric_cells = []
        for cell in cells:
            cell_text = textify_html(cell)
            if re.fullmatch(r"\d{1,3}(?:\.\d+)?%?", cell_text):
                numeric_cells.append(float(cell_text.rstrip("%")))
        if numeric_cells:
            if score_index is not None and 0 <= score_index < len(numeric_cells):
                return numeric_cells[score_index]
            return numeric_cells[-1]
    return None


def extract_score_near_alias(text: str, aliases: list[str], min_score: float = 0) -> float | None:
    for alias in aliases:
        match = re.search(re.escape(alias), text, flags=re.IGNORECASE)
        if not match:
            continue
        window = text[match.start():match.start() + 500]
        numbers = re.findall(r"(?<![\w.])(\d{1,3}(?:\.\d+)?)(?:\s*%)?", window)
        plausible = [
            float(number)
            for number in numbers
            if min_score <= float(number) <= 100 and not re.fullmatch(r"20\d{2}", number)
        ]
        if plausible:
            return plausible[0]
    return None


def source_to_scores(source: dict, raw: str) -> tuple[list[dict], list[dict]]:
    text = textify_html(raw)
    today = date.today().isoformat()
    scores = []
    misses = []

    for target in source["targets"]:
        aliases = target.get("aliases", [target["model"]])
        found = extract_score_from_html_row(raw, aliases, source.get("score_index"))
        if found is None:
            found = extract_score_near_alias(text, aliases, source.get("min_score", 0))
        if found is None:
            misses.append(
                {
                    "source": source["id"],
                    "benchmark": target["benchmark"],
                    "provider": target["provider"],
                    "model": target["model"],
                    "aliases": aliases,
                }
            )
            continue
        scores.append(
            {
                "benchmark_id": target["benchmark_id"],
                "benchmark": target["benchmark"],
                "provider": target["provider"],
                "model": target["model"],
                "score": found,
                "metric": source["metric"],
                "higher_is_better": True,
                "reported_date": today,
                "source_type": source["source_type"],
                "source": {"label": source["name"], "url": source["url"]},
                "note": f"Auto-extracted from {source['name']}; review before citing.",
            }
        )
    return scores, misses


def compare_scores(existing: list[dict], proposed: list[dict]) -> list[dict]:
    current = {score_key(score): score for score in existing}
    changes = []
    for score in proposed:
        key = score_key(score)
        old = current.get(key)
        if old is None:
            changes.append({"action": "add", "old": None, "new": score})
        elif float(old["score"]) != float(score["score"]):
            changes.append({"action": "update", "old": old, "new": score})
    return changes


def refresh_scores(source_id: str | None = None, dry_run: bool = False) -> Path:
    sources = load_score_sources()["sources"]
    if source_id:
        sources = [source for source in sources if source["id"] == source_id]
        if not sources:
            raise SystemExit(f"No score source found with id: {source_id}")

    INBOX.mkdir(exist_ok=True)
    proposed = []
    failures = []
    no_matches = []
    extracted_by_source = {}
    for source in sources:
        try:
            raw = fetch_text(source["url"])
            (INBOX / f"{source['id']}.raw.html").write_text(raw, encoding="utf-8")
            source_scores, source_misses = source_to_scores(source, raw)
            proposed.extend(source_scores)
            no_matches.extend(source_misses)
            extracted_by_source[source["id"]] = len(source_scores)
        except Exception as exc:
            failures.append({"source": source["id"], "url": source["url"], "error": str(exc)})
            extracted_by_source[source["id"]] = 0

    data = load_scores()
    changes = compare_scores(data["scores"], proposed)
    output = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_only": True,
        "dry_run": True,
        "sources_checked": [source["id"] for source in sources],
        "extracted_by_source": extracted_by_source,
        "no_matches": no_matches,
        "failures": failures,
        "changes": changes,
        "unchanged_count": max(0, len(proposed) - len(changes)),
    }
    out = INBOX / f"score_updates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote proposed score updates to {out}")
    print(
        f"Found {len(changes)} change(s), {output['unchanged_count']} unchanged row(s), "
        f"{len(no_matches)} no-match target(s), {len(failures)} failure(s)."
    )
    if changes:
        print(f"Review it, then run: python3 scripts/research_agent.py apply-score-updates {out}")
    return out


def apply_score_updates(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        proposal = json.load(f)

    changes = proposal.get("changes", [])
    if not changes:
        print("No changes to apply.")
        return

    data = load_scores()
    scores_by_key = {score_key(score): score for score in data["scores"]}
    for change in changes:
        new_score = change["new"]
        errors = validate_score(new_score)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            raise SystemExit(2)
        scores_by_key[score_key(new_score)] = new_score

    data["scores"] = sorted(
        scores_by_key.values(),
        key=lambda score: (score["benchmark"].lower(), score["provider"].lower(), score["model"].lower()),
    )
    save_scores(data)
    print(f"Applied {len(changes)} score update(s) to {SCORES_FILE}")


def infer_provider(model_name: str) -> str:
    lower = model_name.lower()
    provider_rules = [
        ("OpenAI", ["gpt", "o3", "o4"]),
        ("Anthropic", ["claude"]),
        ("Google", ["gemini", "gemma"]),
        ("Meta", ["llama"]),
        ("Alibaba", ["qwen"]),
        ("DeepSeek", ["deepseek"]),
        ("xAI", ["grok"]),
        ("Mistral", ["mistral", "mixtral"]),
        ("Microsoft", ["phi"]),
        ("Distyl AI", ["buttonagent"]),
    ]
    for provider, needles in provider_rules:
        if any(needle in lower for needle in needles):
            return provider
    return "Other"


def parse_tablebench_history(raw: str) -> list[dict]:
    rows = re.findall(r"<tr\b[^>]*>.*?</tr>", raw, flags=re.IGNORECASE | re.DOTALL)
    history = []
    for row in rows:
        cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, flags=re.IGNORECASE | re.DOTALL)
        if len(cells) != 7:
            continue

        values = []
        for cell in cells:
            text = re.sub(r"<br\s*/?>", " / ", cell, flags=re.IGNORECASE)
            text = textify_html(text)
            values.append(text)

        date_text, model_text, fc, nr, da, viz, overall = values
        if not re.search(r"\d{4}", date_text):
            continue
        numeric_score = r"\d{1,3}(?:\.\d+)?"
        if not all(re.fullmatch(numeric_score, value) for value in [fc, nr, da, viz, overall]):
            continue

        model_name = model_text.split("/")[0].strip()
        method = None
        method_match = re.search(r"\+\s*(DP|TCoT|SCoT|PoT)\b", model_name)
        if method_match:
            method = method_match.group(1)
            model_name = re.sub(r"\s*\+\s*(DP|TCoT|SCoT|PoT)\b", "", model_name).strip()

        try:
            reported_date = datetime.strptime(date_text, "%b %d, %Y").date().isoformat()
        except ValueError:
            continue

        history.append(
            {
                "benchmark_id": "tablebench",
                "benchmark": "TableBench",
                "provider": infer_provider(model_name),
                "model": model_name,
                "method": method,
                "reported_date": reported_date,
                "scores": {
                    "fact_checking": float(fc),
                    "numerical_reasoning": float(nr),
                    "data_analysis": float(da),
                    "visualization": float(viz),
                    "overall": float(overall),
                },
                "source": {
                    "label": "TableBench leaderboard",
                    "url": "https://tablebench.github.io/",
                },
            }
        )

    return sorted(history, key=lambda item: (item["reported_date"], item["provider"], item["model"]))


def refresh_tablebench_history() -> None:
    source = next(source for source in load_score_sources()["sources"] if source["id"] == "tablebench")
    raw = fetch_text(source["url"])
    INBOX.mkdir(exist_ok=True)
    (INBOX / "tablebench.raw.html").write_text(raw, encoding="utf-8")
    history = parse_tablebench_history(raw)
    data = {
        "updated": date.today().isoformat(),
        "metric": "TableBench Overall score",
        "notes": [
            "Rows are parsed from the official TableBench leaderboard.",
            "Provider is inferred from model name; inspect rows before citing provider-level claims.",
            "Multiple rows for one provider may represent different models or prompting methods, not one continuous model lineage.",
        ],
        "history": history,
    }
    with TABLEBENCH_HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(history)} TableBench historical row(s) to {TABLEBENCH_HISTORY_FILE}")


def brief(topic: str) -> None:
    print(f"# Research brief: {topic}\n")
    print("Use this to decide whether the benchmark belongs in the dashboard.\n")
    print("Questions to answer:")
    print("- What capability does this benchmark actually test?")
    print("- Is the task shape close to a data journalism workflow?")
    print("- Are there public examples, a paper, code, data, or leaderboard?")
    print("- What are the strongest caveats or ways the benchmark can mislead?")
    print("- What source should be treated as canonical?\n")
    print("Search starting points:")
    for site in ["arXiv", "Google Scholar", "Hugging Face Papers", "Papers with Code", "GitHub"]:
        query = urllib.parse.quote_plus(topic)
        if site == "arXiv":
            url = f"https://arxiv.org/search/?query={query}&searchtype=all"
        elif site == "Google Scholar":
            url = f"https://scholar.google.com/scholar?q={query}"
        elif site == "Hugging Face Papers":
            url = f"https://huggingface.co/papers?q={query}"
        elif site == "Papers with Code":
            url = f"https://paperswithcode.com/search?q={query}"
        else:
            url = f"https://github.com/search?q={query}&type=repositories"
        print(f"- {site}: {url}")
    print("\nDraft JSON shape:")
    print(json.dumps(SCHEMA_HINT, indent=2))


def add_entry(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        entry = json.load(f)

    if "id" not in entry and "name" in entry:
        entry["id"] = slugify(entry["name"])

    errors = validate_entry(entry)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)

    data = load_dashboard()
    existing_ids = {item["id"] for item in data["benchmarks"]}
    if entry["id"] in existing_ids:
        data["benchmarks"] = [entry if item["id"] == entry["id"] else item for item in data["benchmarks"]]
        action = "Updated"
    else:
        data["benchmarks"].append(entry)
        action = "Added"

    save_dashboard(data)
    print(f"{action} {entry['name']} in {DATA_FILE}")


def call_openai_research(topic: str, model: str) -> Path:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for AI research mode.")

    prompt = f"""
Research this AI benchmark or capability for a personal data journalism benchmark dashboard: {topic}

Return only one JSON object matching this shape:
{json.dumps(SCHEMA_HINT, indent=2)}

Rules:
- Prefer primary sources: official paper pages, project pages, GitHub repos, benchmark maintainers.
- Focus on relevance to data journalism tasks: source discovery, fact checks, tables, charts, documents, coding, analysis.
- Include two signals: one practical strength and one caveat.
- Do not invent performance numbers unless a source explicitly supports them.
"""

    body = {
        "model": model,
        "tools": [{"type": "web_search"}],
        "input": prompt,
        "text": {"format": {"type": "json_object"}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))

    text = payload.get("output_text")
    if not text:
        chunks = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if "text" in content:
                    chunks.append(content["text"])
        text = "\n".join(chunks)

    entry = json.loads(text)
    if "id" not in entry and "name" in entry:
        entry["id"] = slugify(entry["name"])

    INBOX.mkdir(exist_ok=True)
    out = INBOX / f"{slugify(entry.get('name', topic))}.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Research helper for the benchmark dashboard.")
    sub = parser.add_subparsers(dest="command", required=True)

    brief_parser = sub.add_parser("brief", help="Print a research checklist and search links.")
    brief_parser.add_argument("topic")

    add_parser = sub.add_parser("add", help="Validate and add a benchmark JSON file to the dashboard.")
    add_parser.add_argument("path", type=Path)

    research_parser = sub.add_parser("research", help="Use OpenAI Responses API with web search to draft an entry.")
    research_parser.add_argument("topic")
    research_parser.add_argument("--model", default="gpt-5")

    refresh_parser = sub.add_parser("refresh-scores", help="Crawl known score sources and draft proposed updates.")
    refresh_parser.add_argument("--source", help="Only refresh one source id from data/score_sources.json.")
    refresh_parser.add_argument("--dry-run", action="store_true", help="Write a proposal file without applying changes. This is the default behavior.")

    apply_scores_parser = sub.add_parser("apply-score-updates", help="Apply a reviewed score update proposal.")
    apply_scores_parser.add_argument("path", type=Path)

    sub.add_parser("refresh-tablebench-history", help="Fetch and parse the official TableBench historical leaderboard.")

    args = parser.parse_args()
    if args.command == "brief":
        brief(args.topic)
    elif args.command == "add":
        add_entry(args.path)
    elif args.command == "research":
        out = call_openai_research(args.topic, args.model)
        print(f"Wrote draft to {out}")
        print(f"Review it, then run: python3 scripts/research_agent.py add {out}")
    elif args.command == "refresh-scores":
        refresh_scores(args.source, args.dry_run)
    elif args.command == "apply-score-updates":
        apply_score_updates(args.path)
    elif args.command == "refresh-tablebench-history":
        refresh_tablebench_history()


if __name__ == "__main__":
    main()
