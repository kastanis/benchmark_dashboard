# AI Benchmarks for Data Journalism

A small personal dashboard for tracking AI benchmarks that matter for data journalism tasks: finding hard-to-locate facts, checking claims against tables, reasoning over charts, writing analysis code, and working with messy documents.

## Open the dashboard

This is a dependency-free static app:

```bash
cd /Users/akastanis/Git_work/benchmark_dashboard
python3 -m http.server 8765
```

Then open `http://localhost:8765`.

## Refresh the research

The dashboard data lives in `data/benchmarks.json`.
Reported model scores live in `data/model_scores.json`.
Recommended benchmark groups live in `data/benchmark_recommendations.json`.
Parsed TableBench historical rows live in `data/tablebench_history.json`.

Create a research prompt for a new benchmark:

```bash
python3 scripts/research_agent.py brief "new benchmark name or capability"
```

Add a structured finding from notes:

```bash
python3 scripts/research_agent.py add research_inbox/example.json
```

Run optional AI research mode with OpenAI's Responses API and web search:

```bash
export OPENAI_API_KEY=...
python3 scripts/research_agent.py research "benchmark or capability to investigate"
```

AI mode asks for structured JSON and appends a draft entry to `research_inbox/`. Review it, then run `add`.

Refresh known leaderboard sources:

```bash
python3 scripts/research_agent.py refresh-scores
```

This writes a review file like `research_inbox/score_updates_YYYYMMDD_HHMMSS.json`. It never applies score changes directly. After reviewing:

```bash
python3 scripts/research_agent.py apply-score-updates research_inbox/score_updates_YYYYMMDD_HHMMSS.json
```

Known score sources are configured in `data/score_sources.json`.

Refresh TableBench history from the official leaderboard:

```bash
python3 scripts/research_agent.py refresh-tablebench-history
```

## Data model

Each benchmark entry has:

- `name`, `category`, `status`, `year`
- `journalism_relevance`: score from 1-5
- `capabilities`: short tags used by filters
- `why_it_matters`: one-sentence newsroom use case
- `signals`: strengths and caveats
- `source`: canonical URL and short citation label

The goal is not to crown a universal leaderboard winner. It is to keep a pragmatic map of which AI capabilities are becoming useful for reporting workflows.

## Leaderboard notes

Model scores are stored separately from benchmark notes because they change more often. Each score row includes `source_type`:

- `official`: benchmark maintainer or model lab publication.
- `third_party`: aggregator or outside tracker; useful for awareness, but check before citing.

Some rows represent full systems or agents rather than a base model. For journalism use, treat them as signals about a workflow, not as proof that one chatbot is always better than another.

For benchmark definitions and methodology, arXiv papers are good canonical sources. For current model scores, prefer official leaderboards or clearly labeled score aggregators.

## Current categories

The dashboard now tracks five broad watch areas:

- Reasoning / general intelligence
- Code and data work
- Data / analytical reasoning
- Truthfulness / hallucinations
- Unstructured -> structured extraction
- Tool use / agents
