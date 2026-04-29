# Scheduling Score Refreshes

The refresh workflow is review-first:

```bash
cd /Users/akastanis/Git_work/benchmark_dashboard
python3 scripts/research_agent.py refresh-scores
```

That writes a proposed update file in `research_inbox/`. Review it, then apply:

```bash
python3 scripts/research_agent.py apply-score-updates research_inbox/score_updates_YYYYMMDD_HHMMSS.json
```

## macOS launchd

Copy `scripts/com.benchmark-dashboard.refresh-scores.plist` to `~/Library/LaunchAgents/`, then load it:

```bash
cp scripts/com.benchmark-dashboard.refresh-scores.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.benchmark-dashboard.refresh-scores.plist
```

The included template runs weekly on Monday at 9 a.m. and writes logs to `research_inbox/`.

Generated proposal files are ignored by git on purpose. They are working notes for review, not permanent dashboard data.

## Parser Limits

Leaderboard pages change shape often. The refresh command reports:

- `changes`: proposed adds or updates.
- `unchanged_count`: extracted rows that match current dashboard data.
- `no_matches`: configured targets the parser could not confidently extract.
- `failures`: sources that could not be fetched.

Treat `no_matches` as a prompt to inspect the source manually or improve `data/score_sources.json` and the parser.

## Cron

For a simpler weekly cron entry:

```cron
0 9 * * 1 cd /Users/akastanis/Git_work/benchmark_dashboard && /usr/bin/python3 scripts/research_agent.py refresh-scores >> research_inbox/refresh.log 2>&1
```

## GitHub Actions

If this repo moves to GitHub, use a scheduled workflow that runs `refresh-scores` and opens a pull request with the proposed JSON file. That keeps source changes reviewable.
