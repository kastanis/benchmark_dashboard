const state = {
  benchmarks: [],
  filtered: [],
  scores: [],
  filteredScores: [],
  scoreNotes: [],
  recommendationGroups: [],
  tablebenchHistory: [],
};

const els = {
  benchmarkCount: document.querySelector("#benchmarkCount"),
  updatedDate: document.querySelector("#updatedDate"),
  searchInput: document.querySelector("#searchInput"),
  categoryFilter: document.querySelector("#categoryFilter"),
  relevanceFilter: document.querySelector("#relevanceFilter"),
  relevanceValue: document.querySelector("#relevanceValue"),
  capabilityBars: document.querySelector("#capabilityBars"),
  priorityList: document.querySelector("#priorityList"),
  resultCount: document.querySelector("#resultCount"),
  benchmarks: document.querySelector("#benchmarks"),
  template: document.querySelector("#benchmarkTemplate"),
  scoreBenchmarkFilter: document.querySelector("#scoreBenchmarkFilter"),
  scoreProviderFilter: document.querySelector("#scoreProviderFilter"),
  scoreRows: document.querySelector("#scoreRows"),
  scoreNotes: document.querySelector("#scoreNotes"),
  recommendationGroups: document.querySelector("#recommendationGroups"),
  trendChart: document.querySelector("#trendChart"),
  trendTooltip: document.querySelector("#trendTooltip"),
  trendSummary: document.querySelector("#trendSummary"),
  trendLegend: document.querySelector("#trendLegend"),
};

async function loadData() {
  const [benchmarkResponse, scoreResponse, recommendationResponse, tablebenchHistoryResponse] = await Promise.all([
    fetch("data/benchmarks.json"),
    fetch("data/model_scores.json"),
    fetch("data/benchmark_recommendations.json"),
    fetch("data/tablebench_history.json"),
  ]);
  if (!benchmarkResponse.ok) {
    throw new Error(`Could not load benchmark data: ${benchmarkResponse.status}`);
  }
  if (!scoreResponse.ok) {
    throw new Error(`Could not load score data: ${scoreResponse.status}`);
  }
  if (!recommendationResponse.ok) {
    throw new Error(`Could not load recommendation data: ${recommendationResponse.status}`);
  }
  if (!tablebenchHistoryResponse.ok) {
    throw new Error(`Could not load TableBench history data: ${tablebenchHistoryResponse.status}`);
  }
  const data = await benchmarkResponse.json();
  const scoreData = await scoreResponse.json();
  const recommendationData = await recommendationResponse.json();
  const tablebenchHistoryData = await tablebenchHistoryResponse.json();
  state.benchmarks = data.benchmarks;
  state.filtered = data.benchmarks;
  state.scores = scoreData.scores;
  state.filteredScores = scoreData.scores;
  state.scoreNotes = scoreData.notes || [];
  state.recommendationGroups = recommendationData.groups || [];
  state.tablebenchHistory = tablebenchHistoryData.history || [];
  els.benchmarkCount.textContent = data.benchmarks.length;
  els.updatedDate.textContent = data.updated;
  populateCategoryFilter(data.benchmarks);
  populateScoreFilters(scoreData.scores);
  render();
}

function populateCategoryFilter(benchmarks) {
  const categories = [...new Set(benchmarks.map((item) => item.category))].sort();
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    els.categoryFilter.append(option);
  }
}

function populateScoreFilters(scores) {
  const benchmarks = [...new Set(scores.map((item) => item.benchmark))].sort();
  const providers = [...new Set(scores.map((item) => item.provider))].sort();

  for (const benchmark of benchmarks) {
    const option = document.createElement("option");
    option.value = benchmark;
    option.textContent = benchmark;
    els.scoreBenchmarkFilter.append(option);
  }

  for (const provider of providers) {
    const option = document.createElement("option");
    option.value = provider;
    option.textContent = provider;
    els.scoreProviderFilter.append(option);
  }
}

function applyFilters() {
  const query = els.searchInput.value.trim().toLowerCase();
  const category = els.categoryFilter.value;
  const minRelevance = Number(els.relevanceFilter.value);

  state.filtered = state.benchmarks.filter((item) => {
    const haystack = [
      item.name,
      item.category,
      item.why_it_matters,
      item.task_shape,
      ...item.capabilities,
      ...item.signals,
    ].join(" ").toLowerCase();

    return (
      haystack.includes(query) &&
      (category === "all" || item.category === category) &&
      item.journalism_relevance >= minRelevance
    );
  });

  els.relevanceValue.textContent = `${minRelevance}+`;
  renderBenchmarks();
  renderPriorityList();
}

function applyScoreFilters() {
  const benchmark = els.scoreBenchmarkFilter.value;
  const provider = els.scoreProviderFilter.value;

  state.filteredScores = state.scores.filter((item) => {
    return (
      (benchmark === "all" || item.benchmark === benchmark) &&
      (provider === "all" || item.provider === provider)
    );
  });

  renderScoreRows();
}

function render() {
  renderCapabilityBars();
  renderPriorityList();
  renderScoreRows();
  renderTrendChart();
  renderRecommendations();
  renderBenchmarks();
}

function renderCapabilityBars() {
  const counts = new Map();
  for (const item of state.benchmarks) {
    for (const capability of item.capabilities) {
      counts.set(capability, (counts.get(capability) || 0) + 1);
    }
  }

  const rows = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 10);
  const max = Math.max(...rows.map((row) => row[1]));

  els.capabilityBars.replaceChildren();
  for (const [capability, count] of rows) {
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <strong>${capability}</strong>
      <div class="bar-track" aria-hidden="true">
        <div class="bar-fill" style="width: ${(count / max) * 100}%"></div>
      </div>
      <span>${count}</span>
    `;
    els.capabilityBars.append(row);
  }
}

function renderPriorityList() {
  const top = [...state.filtered]
    .sort((a, b) => {
      if (b.journalism_relevance !== a.journalism_relevance) {
        return b.journalism_relevance - a.journalism_relevance;
      }
      return b.year - a.year;
    })
    .slice(0, 5);

  els.priorityList.replaceChildren();
  for (const [index, item] of top.entries()) {
    const row = document.createElement("div");
    row.className = "priority-item";
    row.innerHTML = `
      <div class="rank">${index + 1}</div>
      <div>
        <strong>${item.name}</strong>
        <span>${item.category} / relevance ${item.journalism_relevance}/5</span>
      </div>
    `;
    els.priorityList.append(row);
  }
}

function renderScoreRows() {
  const rows = [...state.filteredScores].sort((a, b) => {
    if (a.benchmark !== b.benchmark) {
      return a.benchmark.localeCompare(b.benchmark);
    }
    return b.score - a.score;
  });
  const maxByBenchmark = new Map();

  for (const item of state.scores) {
    const current = maxByBenchmark.get(item.benchmark) || 0;
    maxByBenchmark.set(item.benchmark, Math.max(current, item.score));
  }

  els.scoreRows.replaceChildren();
  for (const item of rows) {
    const tr = document.createElement("tr");
    const max = maxByBenchmark.get(item.benchmark) || item.score;
    const width = max > 0 ? (item.score / max) * 100 : 0;
    const sourceBadge = item.source_type === "official" ? "official" : "third-party";
    tr.innerHTML = `
      <td><strong>${item.benchmark}</strong><span>${item.reported_date}</span></td>
      <td>${item.provider}</td>
      <td>${item.model}</td>
      <td>
        <div class="score-cell">
          <strong>${formatScore(item.score)}</strong>
          <div class="score-track" aria-hidden="true">
            <div class="score-fill" style="width: ${width}%"></div>
          </div>
        </div>
      </td>
      <td>${item.metric}</td>
      <td><a href="${item.source.url}" target="_blank" rel="noreferrer">${sourceBadge}</a></td>
      <td>${item.note}</td>
    `;
    els.scoreRows.append(tr);
  }

  els.scoreNotes.textContent = state.scoreNotes.join(" ");
}

function renderTrendChart() {
  const points = state.tablebenchHistory.map((item) => ({
    benchmark_id: item.benchmark_id,
    benchmark: item.benchmark,
    provider: item.provider,
    model: item.model,
    metric: "TableBench overall",
    score: item.scores.overall,
    method: item.method,
    reported_date: item.reported_date,
    timestamp: Date.parse(item.reported_date),
  }))
    .filter((item) => Number.isFinite(item.timestamp))
    .sort((a, b) => a.timestamp - b.timestamp);

  const width = 860;
  const height = 300;
  const margin = { top: 22, right: 24, bottom: 42, left: 48 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  els.trendChart.setAttribute("viewBox", `0 0 ${width} ${height}`);
  els.trendChart.replaceChildren();
  els.trendLegend.replaceChildren();

  if (!points.length) {
    els.trendSummary.textContent = "No TableBench history rows are available yet. Run refresh-tablebench-history to rebuild this chart from the official leaderboard.";
    const text = svgEl("text", { x: width / 2, y: height / 2, "text-anchor": "middle", class: "chart-empty" });
    text.textContent = "No trend data yet";
    els.trendChart.append(text);
    return;
  }

  const minTime = Math.min(...points.map((item) => item.timestamp));
  const maxTime = Math.max(...points.map((item) => item.timestamp));
  const minScore = Math.min(0, ...points.map((item) => item.score));
  const maxScore = Math.max(100, ...points.map((item) => item.score));
  const providers = [...new Set(points.map((item) => item.provider))].sort();
  const colors = new Map(providers.map((provider, index) => [provider, providerColor(index)]));

  const x = (timestamp) => {
    if (maxTime === minTime) return margin.left + innerWidth / 2;
    return margin.left + ((timestamp - minTime) / (maxTime - minTime)) * innerWidth;
  };
  const y = (score) => margin.top + innerHeight - ((score - minScore) / (maxScore - minScore)) * innerHeight;

  for (const tick of [0, 25, 50, 75, 100]) {
    const line = svgEl("line", {
      x1: margin.left,
      x2: width - margin.right,
      y1: y(tick),
      y2: y(tick),
      class: "chart-grid",
    });
    const label = svgEl("text", { x: margin.left - 10, y: y(tick) + 4, "text-anchor": "end", class: "chart-label" });
    label.textContent = tick;
    els.trendChart.append(line, label);
  }

  const axis = svgEl("line", {
    x1: margin.left,
    x2: width - margin.right,
    y1: height - margin.bottom,
    y2: height - margin.bottom,
    class: "chart-axis",
  });
  els.trendChart.append(axis);

  const years = [...new Set(points.map((item) => new Date(item.timestamp).getFullYear()))];
  for (const year of years) {
    const timestamp = Date.parse(`${year}-07-01`);
    const label = svgEl("text", {
      x: x(Math.min(Math.max(timestamp, minTime), maxTime)),
      y: height - 14,
      "text-anchor": "middle",
      class: "chart-label",
    });
    label.textContent = year;
    els.trendChart.append(label);
  }

  for (const provider of providers) {
    const providerPoints = points.filter((item) => item.provider === provider);
    const path = providerPoints
      .map((item, index) => `${index === 0 ? "M" : "L"} ${x(item.timestamp).toFixed(1)} ${y(item.score).toFixed(1)}`)
      .join(" ");
    if (providerPoints.length > 1) {
      els.trendChart.append(svgEl("path", { d: path, fill: "none", stroke: colors.get(provider), "stroke-width": 2.5 }));
    }

    for (const item of providerPoints) {
      const circle = svgEl("circle", {
        cx: x(item.timestamp),
        cy: y(item.score),
        r: 5,
        fill: colors.get(provider),
      });
      const title = svgEl("title", {});
      title.textContent = `${item.benchmark}: ${item.provider} ${item.model} scored ${formatScore(item.score)} (${item.reported_date})`;
      circle.append(title);
      circle.classList.add("chart-point");
      circle.setAttribute("tabindex", "0");
      circle.setAttribute("aria-label", title.textContent);
      circle.addEventListener("pointerenter", (event) => showTrendTooltip(event, item));
      circle.addEventListener("pointermove", (event) => positionTrendTooltip(event));
      circle.addEventListener("pointerleave", hideTrendTooltip);
      circle.addEventListener("focus", (event) => showTrendTooltip(event, item));
      circle.addEventListener("blur", hideTrendTooltip);
      els.trendChart.append(circle);
    }
  }

  for (const provider of providers) {
    const item = document.createElement("span");
    item.innerHTML = `<i style="background:${colors.get(provider)}"></i>${provider}`;
    els.trendLegend.append(item);
  }

  const providerCount = new Set(points.map((item) => item.provider)).size;
  els.trendSummary.textContent = `Currently this view has ${points.length} dated TableBench rows covering ${providerCount} providers. A provider line may connect different models or prompting methods from that provider, so read it as a provider-level trajectory rather than a single model's progress.`;
}

function showTrendTooltip(event, item) {
  els.trendTooltip.hidden = false;
  els.trendTooltip.innerHTML = `
    <strong>${item.provider}</strong>
    <span>${item.model}</span>
    <dl>
      <div><dt>Benchmark</dt><dd>${item.benchmark}</dd></div>
      <div><dt>Score</dt><dd>${formatScore(item.score)}</dd></div>
      <div><dt>Metric</dt><dd>${item.metric || "score"}</dd></div>
      <div><dt>Date</dt><dd>${item.reported_date}</dd></div>
      ${item.method ? `<div><dt>Method</dt><dd>${item.method}</dd></div>` : ""}
    </dl>
  `;
  positionTrendTooltip(event);
}

function positionTrendTooltip(event) {
  const wrap = els.trendChart.parentElement.getBoundingClientRect();
  const tooltip = els.trendTooltip;
  const offset = 14;
  const width = tooltip.offsetWidth || 220;
  const height = tooltip.offsetHeight || 130;
  let left = event.clientX - wrap.left + offset;
  let top = event.clientY - wrap.top + offset;

  if (left + width > wrap.width) {
    left = event.clientX - wrap.left - width - offset;
  }
  if (top + height > wrap.height) {
    top = event.clientY - wrap.top - height - offset;
  }

  tooltip.style.left = `${Math.max(8, left)}px`;
  tooltip.style.top = `${Math.max(8, top)}px`;
}

function hideTrendTooltip() {
  els.trendTooltip.hidden = true;
}

function svgEl(name, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, value);
  }
  return el;
}

function providerColor(index) {
  return ["#2f6fed", "#178a63", "#c84630", "#a66b00", "#6f42c1", "#0f766e"][index % 6];
}

function renderRecommendations() {
  els.recommendationGroups.replaceChildren();

  for (const group of state.recommendationGroups) {
    const card = document.createElement("article");
    card.className = "recommendation-card";

    const items = group.recommended.map((item) => `
      <li>
        <div>
          <strong>${item.name}</strong>
          <span>${item.why}</span>
        </div>
        <em>${item.status}</em>
      </li>
    `).join("");

    card.innerHTML = `
      <h3>${group.name}</h3>
      <p>${group.question}</p>
      <ul>${items}</ul>
    `;
    els.recommendationGroups.append(card);
  }
}

function formatScore(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0$/, "").replace(/\.0$/, "");
}

function renderBenchmarks() {
  els.resultCount.textContent = `Showing ${state.filtered.length} ${state.filtered.length === 1 ? "entry" : "entries"}`;
  els.benchmarks.replaceChildren();

  for (const item of state.filtered) {
    const card = els.template.content.cloneNode(true);
    card.querySelector(".category").textContent = item.category;
    card.querySelector(".year").textContent = item.year;
    card.querySelector("h3").textContent = item.name;
    card.querySelector(".why").textContent = item.why_it_matters;
    card.querySelector(".status").textContent = item.status;
    card.querySelector(".difficulty").textContent = item.difficulty;
    card.querySelector(".score").textContent = `${item.journalism_relevance}/5 relevance`;

    const tags = card.querySelector(".tags");
    for (const capability of item.capabilities) {
      const tag = document.createElement("span");
      tag.textContent = capability;
      tags.append(tag);
    }

    const signals = card.querySelector(".signals");
    for (const signal of item.signals) {
      const li = document.createElement("li");
      li.textContent = signal;
      signals.append(li);
    }

    const source = card.querySelector(".source");
    source.href = item.source.url;
    source.textContent = item.source.label;
    els.benchmarks.append(card);
  }
}

for (const control of [els.searchInput, els.categoryFilter, els.relevanceFilter]) {
  control.addEventListener("input", applyFilters);
}

for (const control of [els.scoreBenchmarkFilter, els.scoreProviderFilter]) {
  control.addEventListener("input", applyScoreFilters);
}

loadData().catch((error) => {
  const isFile = window.location.protocol === "file:";
  const message = isFile
    ? "This dashboard needs to be opened from a local web server so the browser can load the JSON files in ./data. Use http://127.0.0.1:8879/ instead of opening index.html directly."
    : `Could not load dashboard data: ${error.message}`;
  els.benchmarks.innerHTML = `<div class="load-error">${message}</div>`;
});
