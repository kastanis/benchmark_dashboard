# How To Make The Agent Work

The dashboard is a static app. The agent is the helper script at:

```bash
scripts/research_agent.py
```

Run commands from the repo root:

```bash
cd /Users/akastanis/Git_work/benchmark_dashboard
```

## Research A New Benchmark

Generate a research brief:

```bash
python3 scripts/research_agent.py brief "MMLU-Pro"
```

This prints:

- research questions to answer
- source links, including arXiv, Google Scholar, Hugging Face Papers, Papers with Code, and GitHub
- the JSON shape expected by the dashboard

## Draft A Benchmark Card With AI

Set your OpenAI API key:

```bash
export OPENAI_API_KEY=...
```

Ask the agent to research and draft a card:

```bash
python3 scripts/research_agent.py research "MMLU-Pro"
```

The agent writes a draft JSON file to `research_inbox/`.

Review the draft. If it looks right, add it to the dashboard:

```bash
python3 scripts/research_agent.py add research_inbox/mmlu-pro.json
```

## Refresh Model Score Proposals

Fetch configured leaderboard sources and write proposed updates:

```bash
python3 scripts/research_agent.py refresh-scores
```

This creates a file like:

```bash
research_inbox/score_updates_YYYYMMDD_HHMMSS.json
```

Review that file. If the proposed changes look right, apply them:

```bash
python3 scripts/research_agent.py apply-score-updates research_inbox/score_updates_YYYYMMDD_HHMMSS.json
```

The score refresh is review-first by design. It does not automatically change `data/model_scores.json`.

## Refresh TableBench Trend Data

Update the TableBench historical trend file from the official TableBench leaderboard:

```bash
python3 scripts/research_agent.py refresh-tablebench-history
```

This updates:

```bash
data/tablebench_history.json
```

The dashboard uses that file for **TableBench Trend (Data Analysis)**.

## Basic Workflow

```text
brief/research -> review JSON -> add/apply -> refresh dashboard
```

The agent helps discover, structure, and propose updates. You stay in control of what enters the dashboard.

