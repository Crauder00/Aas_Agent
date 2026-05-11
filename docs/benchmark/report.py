"""
AAS Benchmark Report Generator
================================
Liest CSV-Ergebnisse aus aas_benchmark.py und erstellt
einen interaktiven HTML-Report mit Charts.

Verwendung:
    python report.py                                  # neueste CSV in results/
    python report.py --input results/benchmark_X.csv  # spezifische CSV
    python report.py --input results/benchmark_X.csv --open  # direkt im Browser öffnen
"""

import csv
import json
import os
import argparse
import statistics
import webbrowser
from datetime import datetime
from pathlib import Path


# ============================================================
#  CSV LADEN
# ============================================================

def load_csv(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            row["latency_ms"] = float(row["latency_ms"])
            row["success"] = row["success"] == "True"
            row["run"] = int(row["run"])
            row["response_size"] = int(row["response_size"]) if row["response_size"] else None
            rows.append(row)
    return rows


def find_latest_csv(directory: str = "benchmark/results") -> str:
    csvs = sorted(Path(directory).glob("benchmark_*.csv"))
    # summary CSVs ausschliessen
    csvs = [f for f in csvs if "_summary" not in f.name]
    if not csvs:
        raise FileNotFoundError(f"Keine benchmark_*.csv Dateien in '{directory}' gefunden.")
    return str(csvs[-1])


# ============================================================
#  STATISTIK BERECHNEN
# ============================================================

def _percentile(data: list[float], p: int) -> float:
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[lo]
    return sorted_data[lo] + (idx - lo) * (sorted_data[hi] - sorted_data[lo])


def compute_stats(rows: list[dict]) -> dict:
    """Berechnet Statistiken pro Szenario und global."""
    by_scenario: dict[str, list] = {}
    for r in rows:
        by_scenario.setdefault(r["scenario"], []).append(r)

    scenarios = []
    for name, data in by_scenario.items():
        latencies = [r["latency_ms"] for r in data if r["success"]]
        errors = [r for r in data if not r["success"]]
        label = data[0]["label"]

        if not latencies:
            continue

        scenarios.append({
            "name": name,
            "label": label,
            "runs": len(data),
            "errors": len(errors),
            "error_rate": round(len(errors) / len(data) * 100, 1),
            "min": round(min(latencies), 1),
            "max": round(max(latencies), 1),
            "mean": round(statistics.mean(latencies), 1),
            "median": round(statistics.median(latencies), 1),
            "p95": round(_percentile(latencies, 95), 1),
            "p99": round(_percentile(latencies, 99), 1),
            "stddev": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 1),
            # Alle Latenz-Werte für Time-Series Chart
            "series": [r["latency_ms"] for r in data],
            "runs_data": [{"run": r["run"], "ms": r["latency_ms"], "ok": r["success"]} for r in data],
        })

    return {"scenarios": scenarios, "source_file": "", "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S")}


# ============================================================
#  HTML REPORT GENERIEREN
# ============================================================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AAS Benchmark Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:        #0d0f14;
    --surface:   #151820;
    --border:    #1f2433;
    --accent:    #00d4ff;
    --accent2:   #ff6b35;
    --accent3:   #7fff6b;
    --muted:     #4a5568;
    --text:      #e2e8f0;
    --text-dim:  #718096;
    --mono:      'IBM Plex Mono', monospace;
    --sans:      'IBM Plex Sans', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-weight: 300;
    line-height: 1.6;
    min-height: 100vh;
  }

  /* HEADER */
  header {
    border-bottom: 1px solid var(--border);
    padding: 2rem 3rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    background: linear-gradient(135deg, #0d0f14 0%, #111827 100%);
  }

  .header-left h1 {
    font-family: var(--mono);
    font-size: 1.4rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: -0.02em;
  }

  .header-left .subtitle {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-family: var(--mono);
    margin-top: 0.25rem;
  }

  .header-right {
    text-align: right;
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  .header-right .source {
    color: var(--accent);
    font-size: 0.7rem;
  }

  /* LAYOUT */
  main {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2.5rem 3rem;
    display: flex;
    flex-direction: column;
    gap: 2.5rem;
  }

  /* SECTION LABEL */
  .section-label {
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 1rem;
    padding-left: 2px;
    border-left: 2px solid var(--accent);
    padding-left: 0.75rem;
  }

  /* KPI GRID */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
  }

  .kpi-card {
    background: var(--surface);
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
  }

  .kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
  }

  .kpi-card.accent2::before { background: var(--accent2); }
  .kpi-card.accent3::before { background: var(--accent3); }

  .kpi-label {
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 0.5rem;
  }

  .kpi-value {
    font-family: var(--mono);
    font-size: 2rem;
    font-weight: 600;
    color: var(--accent);
    line-height: 1;
  }

  .kpi-card.accent2 .kpi-value { color: var(--accent2); }
  .kpi-card.accent3 .kpi-value { color: var(--accent3); }

  .kpi-unit {
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-top: 0.25rem;
  }

  /* SCENARIO TABS */
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border);
    overflow-x: auto;
  }

  .tab-btn {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 0.75rem;
    padding: 0.75rem 1.5rem;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;
    letter-spacing: 0.05em;
  }

  .tab-btn:hover { color: var(--text); }
  .tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* STATS TABLE */
  .stats-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--mono);
    font-size: 0.8rem;
  }

  .stats-table th {
    text-align: left;
    color: var(--text-dim);
    font-weight: 400;
    letter-spacing: 0.08em;
    font-size: 0.65rem;
    text-transform: uppercase;
    padding: 0.6rem 1rem;
    border-bottom: 1px solid var(--border);
  }

  .stats-table td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
    color: var(--text);
  }

  .stats-table tr:last-child td { border-bottom: none; }

  .stats-table tr:hover td { background: rgba(255,255,255,0.02); }

  .val-accent { color: var(--accent); font-weight: 600; }
  .val-warn   { color: var(--accent2); }
  .val-ok     { color: var(--accent3); }

  /* CHARTS */
  .chart-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }

  @media (max-width: 900px) {
    .chart-grid { grid-template-columns: 1fr; }
    header { flex-direction: column; gap: 1rem; align-items: flex-start; }
    main { padding: 1.5rem; }
  }

  .chart-card {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 1.5rem;
  }

  .chart-card h3 {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 1.2rem;
  }

  .chart-card canvas { width: 100% !important; }

  /* COMPARISON TABLE */
  .comparison-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    overflow-x: auto;
  }

  .badge {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.6rem;
    padding: 0.15rem 0.5rem;
    border-radius: 2px;
    font-weight: 600;
    letter-spacing: 0.05em;
  }

  .badge-ok  { background: rgba(127,255,107,0.12); color: var(--accent3); }
  .badge-err { background: rgba(255,107,53,0.12);  color: var(--accent2); }

  /* FOOTER */
  footer {
    border-top: 1px solid var(--border);
    padding: 1.5rem 3rem;
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--text-dim);
    display: flex;
    justify-content: space-between;
  }
</style>
</head>
<body>

<header>
  <div class="header-left">
    <h1>// AAS BENCHMARK REPORT</h1>
    <div class="subtitle">BaSyx Asset Administration Shell Server · Performance Analysis</div>
  </div>
  <div class="header-right">
    <div>Generated: <span id="gen-time"></span></div>
    <div class="source" id="source-file"></div>
  </div>
</header>

<main>

  <!-- KPI Overview -->
  <section>
    <div class="section-label">Overview</div>
    <div class="kpi-grid" id="kpi-grid"></div>
  </section>

  <!-- Comparison Table -->
  <section>
    <div class="section-label">Szenario Vergleich</div>
    <div class="comparison-wrap">
      <table class="stats-table" id="compare-table">
        <thead>
          <tr>
            <th>Szenario</th>
            <th>Runs</th>
            <th>Fehler</th>
            <th>Min</th>
            <th>Median (p50)</th>
            <th>Mean</th>
            <th>p95</th>
            <th>p99</th>
            <th>Max</th>
            <th>Stddev</th>
          </tr>
        </thead>
        <tbody id="compare-body"></tbody>
      </table>
    </div>
  </section>

  <!-- Per-Scenario Detail Tabs -->
  <section>
    <div class="section-label">Detailansicht pro Szenario</div>
    <div class="tabs" id="tabs"></div>
    <div id="tab-panels" style="margin-top: 1.5rem;"></div>
  </section>

</main>

<footer>
  <span>AAS Benchmark Report · aas_benchmark.py</span>
  <span id="footer-time"></span>
</footer>

<script>
// ── DATA injected by Python ──────────────────────────────────
const REPORT = __REPORT_DATA__;
// ────────────────────────────────────────────────────────────

const COLORS = ['#00d4ff','#ff6b35','#7fff6b','#c084fc','#facc15','#f472b6'];

function fmt(v) { return v != null ? v.toFixed(1) + ' ms' : '—'; }

// Header
document.getElementById('gen-time').textContent = REPORT.generated_at;
document.getElementById('source-file').textContent = REPORT.source_file;
document.getElementById('footer-time').textContent = REPORT.generated_at;

const scenarios = REPORT.scenarios;

// ── KPI Grid ─────────────────────────────────────────────────
function buildKPIs() {
  const grid = document.getElementById('kpi-grid');
  const totalRuns = scenarios.reduce((s, sc) => s + sc.runs, 0);
  const totalErrors = scenarios.reduce((s, sc) => s + sc.errors, 0);
  const allMedians = scenarios.map(s => s.median);
  const bestMedian = Math.min(...allMedians);
  const worstP99 = Math.max(...scenarios.map(s => s.p99));

  const kpis = [
    { label: 'Total Runs',       value: totalRuns,              unit: 'Messungen',  cls: '' },
    { label: 'Gesamt Fehler',    value: totalErrors,            unit: 'Fehler',     cls: 'accent2' },
    { label: 'Bestes Median',    value: bestMedian.toFixed(1),  unit: 'ms',         cls: '' },
    { label: 'Schlechtestes p99',value: worstP99.toFixed(1),    unit: 'ms',         cls: 'accent2' },
    { label: 'Szenarien',        value: scenarios.length,       unit: 'getestet',   cls: 'accent3' },
  ];

  kpis.forEach(k => {
    grid.innerHTML += `
      <div class="kpi-card ${k.cls}">
        <div class="kpi-label">${k.label}</div>
        <div class="kpi-value">${k.value}</div>
        <div class="kpi-unit">${k.unit}</div>
      </div>`;
  });
}

// ── Comparison Table ──────────────────────────────────────────
function buildCompareTable() {
  const tbody = document.getElementById('compare-body');
  scenarios.forEach((sc, i) => {
    const errBadge = sc.errors > 0
      ? `<span class="badge badge-err">${sc.errors} ERR</span>`
      : `<span class="badge badge-ok">OK</span>`;

    tbody.innerHTML += `
      <tr>
        <td style="color:${COLORS[i % COLORS.length]};font-weight:600">${sc.label}</td>
        <td>${sc.runs}</td>
        <td>${errBadge}</td>
        <td>${fmt(sc.min)}</td>
        <td class="val-accent">${fmt(sc.median)}</td>
        <td>${fmt(sc.mean)}</td>
        <td class="val-warn">${fmt(sc.p95)}</td>
        <td class="val-warn">${fmt(sc.p99)}</td>
        <td>${fmt(sc.max)}</td>
        <td>${fmt(sc.stddev)}</td>
      </tr>`;
  });
}

// ── Tabs ──────────────────────────────────────────────────────
function buildTabs() {
  const tabs = document.getElementById('tabs');
  const panels = document.getElementById('tab-panels');

  scenarios.forEach((sc, i) => {
    // Tab button
    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (i === 0 ? ' active' : '');
    btn.textContent = sc.name;
    btn.dataset.idx = i;
    btn.onclick = () => switchTab(i);
    tabs.appendChild(btn);

    // Panel
    const panel = document.createElement('div');
    panel.className = 'tab-panel' + (i === 0 ? ' active' : '');
    panel.id = `panel-${i}`;
    panel.innerHTML = `
      <div class="chart-grid">
        <div class="chart-card">
          <h3>Latenz über Zeit (ms)</h3>
          <canvas id="chart-ts-${i}" height="200"></canvas>
        </div>
        <div class="chart-card">
          <h3>Verteilung (Histogramm)</h3>
          <canvas id="chart-hist-${i}" height="200"></canvas>
        </div>
        <div class="chart-card">
          <h3>Perzentile</h3>
          <canvas id="chart-perc-${i}" height="200"></canvas>
        </div>
        <div class="chart-card">
          <h3>Box Plot (Min / p25 / Median / p75 / Max)</h3>
          <canvas id="chart-box-${i}" height="200"></canvas>
        </div>
      </div>`;
    panels.appendChild(panel);
  });

  // Render charts for first tab immediately
  renderChartsForScenario(0);
}

const renderedTabs = new Set();

function switchTab(idx) {
  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active', i === idx);
  });
  document.querySelectorAll('.tab-panel').forEach((p, i) => {
    p.classList.toggle('active', i === idx);
  });
  if (!renderedTabs.has(idx)) renderChartsForScenario(idx);
}

// ── Chart Rendering ───────────────────────────────────────────
const chartDefaults = {
  color: '#718096',
  borderColor: '#1f2433',
};

Chart.defaults.color = '#718096';
Chart.defaults.borderColor = '#1f2433';

function _pct(arr, p) {
  const s = [...arr].sort((a,b) => a-b);
  const idx = (s.length - 1) * p / 100;
  const lo = Math.floor(idx), hi = lo + 1;
  if (hi >= s.length) return s[lo];
  return s[lo] + (idx - lo) * (s[hi] - s[lo]);
}

function renderChartsForScenario(idx) {
  renderedTabs.add(idx);
  const sc = scenarios[idx];
  const color = COLORS[idx % COLORS.length];
  const latencies = sc.runs_data.map(r => r.ms);
  const labels = sc.runs_data.map(r => r.run);

  // 1) Time Series
  new Chart(document.getElementById(`chart-ts-${idx}`), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Latenz (ms)',
        data: latencies,
        borderColor: color,
        backgroundColor: color + '18',
        borderWidth: 1.5,
        pointRadius: latencies.length > 50 ? 0 : 3,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.2,
      }, {
        label: 'Median',
        data: Array(latencies.length).fill(sc.median),
        borderColor: '#ffffff30',
        borderWidth: 1,
        borderDash: [4, 4],
        pointRadius: 0,
        fill: false,
      }]
    },
    options: {
      responsive: true,
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 10, font: { family: 'IBM Plex Mono', size: 10 } } },
        y: { ticks: { font: { family: 'IBM Plex Mono', size: 10 }, callback: v => v + ' ms' } }
      }
    }
  });

  // 2) Histogram
  const bins = 20;
  const minV = Math.min(...latencies), maxV = Math.max(...latencies);
  const step = (maxV - minV) / bins || 1;
  const counts = Array(bins).fill(0);
  latencies.forEach(v => {
    const b = Math.min(Math.floor((v - minV) / step), bins - 1);
    counts[b]++;
  });
  const binLabels = counts.map((_, i) => (minV + i * step).toFixed(0) + ' ms');

  new Chart(document.getElementById(`chart-hist-${idx}`), {
    type: 'bar',
    data: {
      labels: binLabels,
      datasets: [{ label: 'Häufigkeit', data: counts, backgroundColor: color + 'aa', borderWidth: 0 }]
    },
    options: {
      responsive: true,
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { family: 'IBM Plex Mono', size: 10 } } },
        y: { ticks: { font: { family: 'IBM Plex Mono', size: 10 } } }
      }
    }
  });

  // 3) Percentile Bar
  new Chart(document.getElementById(`chart-perc-${idx}`), {
    type: 'bar',
    data: {
      labels: ['Min', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99', 'Max'],
      datasets: [{
        label: 'ms',
        data: [
          sc.min,
          _pct(latencies, 25),
          sc.median,
          _pct(latencies, 75),
          _pct(latencies, 90),
          sc.p95,
          sc.p99,
          sc.max,
        ],
        backgroundColor: [
          color + '44', color + '55', color + '88', color + 'aa',
          color + 'bb', color + 'cc', color + 'ee', color,
        ],
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      animation: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { font: { family: 'IBM Plex Mono', size: 10 }, callback: v => v + ' ms' } },
        y: { ticks: { font: { family: 'IBM Plex Mono', size: 10 } } }
      }
    }
  });

  // 4) Box Plot (simulated with floating bars)
  const p25 = _pct(latencies, 25);
  const p75 = _pct(latencies, 75);

  new Chart(document.getElementById(`chart-box-${idx}`), {
    type: 'bar',
    data: {
      labels: ['Verteilung'],
      datasets: [
        // Min whisker (invisible base)
        { label: 'Min', data: [[sc.min, sc.min]], backgroundColor: 'transparent', borderColor: color, borderWidth: 2, barThickness: 2 },
        // IQR box
        { label: 'IQR (p25–p75)', data: [[p25, p75]], backgroundColor: color + '44', borderColor: color, borderWidth: 1.5, barThickness: 60 },
        // Median line
        { label: 'Median', data: [[sc.median - 0.5, sc.median + 0.5]], backgroundColor: color, borderWidth: 0, barThickness: 60 },
      ]
    },
    options: {
      responsive: true,
      animation: false,
      plugins: {
        legend: { display: true, labels: { font: { family: 'IBM Plex Mono', size: 10 }, color: '#718096' } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const stats = [
                `Min: ${sc.min} ms`,
                `p25: ${p25.toFixed(1)} ms`,
                `Median: ${sc.median} ms`,
                `p75: ${p75.toFixed(1)} ms`,
                `Max: ${sc.max} ms`,
              ];
              return stats;
            }
          }
        }
      },
      scales: {
        x: { stacked: false, ticks: { font: { family: 'IBM Plex Mono', size: 10 } } },
        y: { ticks: { font: { family: 'IBM Plex Mono', size: 10 }, callback: v => v + ' ms' } }
      }
    }
  });
}

// ── Init ──────────────────────────────────────────────────────
buildKPIs();
buildCompareTable();
buildTabs();
</script>
</body>
</html>
"""


def generate_report(input_csv: str, output_html: str = None, open_browser: bool = False):
    print(f"\n  📂 Lade CSV: {input_csv}")
    rows = load_csv(input_csv)
    print(f"     → {len(rows)} Zeilen geladen")

    stats = compute_stats(rows)
    stats["source_file"] = os.path.basename(input_csv)

    # Output Pfad
    if output_html is None:
        base = input_csv.replace(".csv", "")
        output_html = base + "_report.html"

    # JSON in Template einsetzen
    report_json = json.dumps(stats, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__REPORT_DATA__", report_json)

    os.makedirs(os.path.dirname(os.path.abspath(output_html)), exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  ✅ Report erstellt: {output_html}")

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(output_html)}")
        print(f"  🌐 Im Browser geöffnet")

    return output_html


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="AAS Benchmark Report Generator")
    parser.add_argument("--input",  type=str, default=None,  help="Pfad zur benchmark_*.csv (default: neueste in results/)")
    parser.add_argument("--output", type=str, default=None,  help="Ausgabe HTML-Datei (default: neben der CSV)")
    parser.add_argument("--open",   action="store_true",     help="Report direkt im Browser öffnen")
    args = parser.parse_args()

    input_csv = args.input or find_latest_csv()
    generate_report(input_csv, args.output, args.open)


if __name__ == "__main__":
    main()
