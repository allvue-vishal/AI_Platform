"""HTML dashboard report generator — inspired by llm-stats.com."""

from __future__ import annotations

import json
import os
from datetime import datetime

from jinja2 import Template

from benchmarks.base import BenchmarkResult
from config import settings


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LLM Benchmark Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root{--bg:#09090b;--bg2:#18181b;--card:#1c1c21;--border:#27272a;--text:#fafafa;--muted:#a1a1aa;--accent:#3b82f6;--accent2:#6366f1;--green:#22c55e;--yellow:#eab308;--red:#ef4444;--orange:#f97316;--ring:rgba(59,130,246,0.15)}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
  a{color:var(--accent);text-decoration:none}
  a:hover{text-decoration:underline}

  /* Header */
  .header{background:var(--bg2);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}
  .header h1{font-size:1.3rem;font-weight:700;display:flex;align-items:center;gap:.5rem}
  .header h1 span{color:var(--accent)}
  .header-meta{color:var(--muted);font-size:.85rem}

  /* Layout */
  .container{max-width:1280px;margin:0 auto;padding:1.5rem 2rem}

  /* Nav tabs */
  .nav-tabs{display:flex;gap:.25rem;border-bottom:1px solid var(--border);margin-bottom:1.5rem;overflow-x:auto}
  .nav-tab{padding:.65rem 1.2rem;font-size:.875rem;font-weight:500;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s}
  .nav-tab:hover{color:var(--text)}
  .nav-tab.active{color:var(--accent);border-bottom-color:var(--accent)}

  /* Tab content */
  .tab-content{display:none}
  .tab-content.active{display:block}

  /* Stats strip */
  .stats-strip{display:flex;gap:1rem;margin-bottom:1.5rem;flex-wrap:wrap}
  .stat-pill{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.75rem 1.25rem;flex:1;min-width:140px;text-align:center}
  .stat-pill .val{font-size:1.5rem;font-weight:800;color:var(--accent)}
  .stat-pill .lbl{font-size:.75rem;color:var(--muted);margin-top:2px;text-transform:uppercase;letter-spacing:.05em}

  /* Cards grid */
  .cat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin-bottom:2rem}
  .cat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.25rem;cursor:pointer;transition:all .2s}
  .cat-card:hover{border-color:var(--accent);box-shadow:0 0 0 3px var(--ring)}
  .cat-card .cat-count{font-size:1.8rem;font-weight:800;color:var(--accent);margin-bottom:.25rem}
  .cat-card .cat-name{font-weight:600;font-size:1rem;margin-bottom:.25rem}
  .cat-card .cat-desc{font-size:.8rem;color:var(--muted)}

  /* Section */
  .section{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.5rem;margin-bottom:1.5rem}
  .section h2{font-size:1.15rem;font-weight:700;margin-bottom:1rem;display:flex;align-items:center;gap:.5rem}
  .section h2 .badge{background:var(--accent);color:#fff;font-size:.7rem;padding:2px 8px;border-radius:6px;font-weight:600}

  /* Tables */
  table{width:100%;border-collapse:collapse}
  thead th{text-align:left;padding:10px 14px;font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--border);cursor:pointer;user-select:none;white-space:nowrap}
  thead th:hover{color:var(--text)}
  tbody td{padding:10px 14px;border-bottom:1px solid var(--border);font-size:.9rem}
  tbody tr:hover{background:rgba(255,255,255,.03)}
  .rank{font-weight:700;color:var(--muted);width:40px}
  .rank-1{color:var(--yellow)}
  .rank-2{color:#c0c0c0}
  .rank-3{color:#cd7f32}
  .model-name{font-weight:600}
  .score-bar-cell{width:220px}
  .score-bar-wrap{display:flex;align-items:center;gap:8px}
  .score-bar-bg{flex:1;height:8px;background:var(--border);border-radius:4px;overflow:hidden}
  .score-bar-fill{height:100%;border-radius:4px;transition:width .4s}
  .score-val{font-weight:700;min-width:45px;text-align:right}
  .high{color:var(--green)}.mid{color:var(--yellow)}.low{color:var(--red)}.med{color:var(--orange)}

  /* Charts */
  .chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem}
  .chart-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.25rem}
  .chart-box h3{font-size:.95rem;font-weight:600;margin-bottom:.75rem;color:var(--muted)}
  .chart-box.full{grid-column:1/-1}
  canvas{max-height:400px}

  /* Winner banner */
  .winner{background:linear-gradient(135deg,#1e1b4b 0%,#172554 50%,#0c4a6e 100%);border:1px solid var(--accent);border-radius:14px;padding:2rem;text-align:center;margin-bottom:1.5rem;position:relative;overflow:hidden}
  .winner::before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 50% 0%,rgba(59,130,246,.15),transparent 70%)}
  .winner h2{color:var(--accent);font-size:1rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem;position:relative}
  .winner .name{font-size:2.2rem;font-weight:800;color:var(--text);position:relative}
  .winner .meta{color:var(--muted);font-size:.95rem;margin-top:.5rem;position:relative}

  /* Best badge */
  .best-pill{background:var(--green);color:#000;padding:2px 10px;border-radius:6px;font-size:.75rem;font-weight:700}

  @media(max-width:768px){.chart-grid{grid-template-columns:1fr}.container{padding:1rem}}
</style>
</head>
<body>

<!-- Sticky Header -->
<div class="header">
  <h1><span>LLM</span> Benchmark Dashboard</h1>
  <div class="header-meta">Generated {{ timestamp }} &middot; {{ num_models }} models &middot; {{ num_categories }} categories</div>
</div>

<div class="container">

<!-- Navigation Tabs -->
<div class="nav-tabs">
  <div class="nav-tab active" onclick="showTab('overview')">Overview</div>
  {% for cat in categories %}
  <div class="nav-tab" onclick="showTab('cat_{{ loop.index }}')">{{ cat }}</div>
  {% endfor %}
  <div class="nav-tab" onclick="showTab('compare')">Compare</div>
</div>

<!-- ==================== OVERVIEW TAB ==================== -->
<div id="tab_overview" class="tab-content active">

  <!-- Stats -->
  <div class="stats-strip">
    <div class="stat-pill"><div class="val">{{ num_models }}</div><div class="lbl">Models Tested</div></div>
    <div class="stat-pill"><div class="val">{{ num_categories }}</div><div class="lbl">Categories</div></div>
    <div class="stat-pill"><div class="val">{{ total_tasks }}</div><div class="lbl">Tasks Run</div></div>
    <div class="stat-pill"><div class="val">{{ total_tokens_all }}</div><div class="lbl">Total Tokens</div></div>
    <div class="stat-pill"><div class="val">${{ total_cost_all }}</div><div class="lbl">Total Cost</div></div>
  </div>

  <!-- Overall Winner -->
  <div class="winner">
    <h2>Overall Best Model</h2>
    <div class="name">{{ overall_winner.model }}</div>
    <div class="meta">Average Score: {{ "%.1f"|format(overall_winner.avg_score) }}/100 &middot; Avg Latency: {{ "%.2f"|format(overall_winner.avg_latency) }}s</div>
  </div>

  <!-- Category cards -->
  <div class="section">
    <h2>Browse by Category <span class="badge">{{ num_categories }}</span></h2>
    <div class="cat-grid">
      {% for cat in categories %}
      <div class="cat-card" onclick="showTab('cat_{{ loop.index }}')">
        <div class="cat-count">{{ category_task_counts[cat] }}</div>
        <div class="cat-name">{{ cat }}</div>
        <div class="cat-desc">Best: {{ best_per_cat[cat].model if best_per_cat.get(cat) else '—' }} ({{ "%.1f"|format(best_per_cat[cat].avg_score) if best_per_cat.get(cat) else '—' }})</div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- Overall Leaderboard -->
  <div class="section">
    <h2>Overall Leaderboard <span class="badge">{{ num_models }} models</span></h2>
    <table id="overallTable">
      <thead><tr>
        <th onclick="sortTbl('overallTable',0)">#</th>
        <th onclick="sortTbl('overallTable',1)">Model</th>
        <th onclick="sortTbl('overallTable',2)">Score</th>
        <th onclick="sortTbl('overallTable',3)">Avg Latency</th>
        <th onclick="sortTbl('overallTable',4)">Total Tokens</th>
        <th onclick="sortTbl('overallTable',5)">Est. Cost</th>
      </tr></thead>
      <tbody>
        {% for m in overall_leaderboard %}
        <tr>
          <td class="rank {{ 'rank-1' if loop.index==1 else ('rank-2' if loop.index==2 else ('rank-3' if loop.index==3 else '')) }}">{{ loop.index }}</td>
          <td class="model-name">{{ m.model }}</td>
          <td class="score-bar-cell">
            <div class="score-bar-wrap">
              <div class="score-bar-bg"><div class="score-bar-fill" style="width:{{ m.avg_score }}%;background:{{ 'var(--green)' if m.avg_score>=80 else ('var(--yellow)' if m.avg_score>=60 else 'var(--red)') }}"></div></div>
              <span class="score-val {{ 'high' if m.avg_score>=80 else ('mid' if m.avg_score>=60 else 'low') }}">{{ "%.1f"|format(m.avg_score) }}</span>
            </div>
          </td>
          <td>{{ "%.2f"|format(m.avg_latency) }}s</td>
          <td>{{ "{:,}".format(m.total_tokens) }}</td>
          <td>${{ "%.6f"|format(m.total_cost) }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Best Model Recommendations -->
  <div class="section">
    <h2>Best Model per Use Case</h2>
    <table>
      <thead><tr><th>Use Case</th><th>Recommended Model</th><th>Score</th><th>Latency</th><th>Cost</th></tr></thead>
      <tbody>
        {% for cat in categories %}
        {% if best_per_cat.get(cat) %}
        <tr>
          <td style="font-weight:600">{{ cat }}</td>
          <td><span class="best-pill">{{ best_per_cat[cat].model }}</span></td>
          <td class="high" style="font-weight:700">{{ "%.1f"|format(best_per_cat[cat].avg_score) }}</td>
          <td>{{ "%.2f"|format(best_per_cat[cat].avg_latency) }}s</td>
          <td>${{ "%.6f"|format(best_per_cat[cat].estimated_cost) }}</td>
        </tr>
        {% endif %}
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<!-- ==================== PER-CATEGORY TABS ==================== -->
{% for cat in categories %}
<div id="tab_cat_{{ loop.index }}" class="tab-content">

  <h2 style="font-size:1.5rem;margin-bottom:.25rem">{{ cat }}</h2>
  <p style="color:var(--muted);margin-bottom:1.5rem;font-size:.9rem">{{ category_descriptions.get(cat, '') }} &middot; {{ category_task_counts[cat] }} tasks</p>

  <!-- Per-category leaderboard -->
  <div class="section">
    <h2>{{ cat }} Leaderboard <span class="badge">{{ num_models }} models</span></h2>
    <table id="catTable_{{ loop.index }}">
      <thead><tr>
        <th onclick="sortTbl('catTable_{{ loop.index }}',0)">#</th>
        <th onclick="sortTbl('catTable_{{ loop.index }}',1)">Model</th>
        <th onclick="sortTbl('catTable_{{ loop.index }}',2)">Score</th>
        <th onclick="sortTbl('catTable_{{ loop.index }}',3)">Avg Latency</th>
        <th onclick="sortTbl('catTable_{{ loop.index }}',4)">Tokens</th>
        <th onclick="sortTbl('catTable_{{ loop.index }}',5)">Cost</th>
      </tr></thead>
      <tbody>
        {% for r in category_leaderboards[cat] %}
        <tr>
          <td class="rank {{ 'rank-1' if loop.index==1 else ('rank-2' if loop.index==2 else ('rank-3' if loop.index==3 else '')) }}">{{ loop.index }}</td>
          <td class="model-name">{{ r.model }}{% if loop.index == 1 %} <span class="best-pill">BEST</span>{% endif %}</td>
          <td class="score-bar-cell">
            <div class="score-bar-wrap">
              <div class="score-bar-bg"><div class="score-bar-fill" style="width:{{ r.avg_score }}%;background:{{ 'var(--green)' if r.avg_score>=80 else ('var(--yellow)' if r.avg_score>=60 else 'var(--red)') }}"></div></div>
              <span class="score-val {{ 'high' if r.avg_score>=80 else ('mid' if r.avg_score>=60 else 'low') }}">{{ "%.1f"|format(r.avg_score) }}</span>
            </div>
          </td>
          <td>{{ "%.2f"|format(r.avg_latency) }}s</td>
          <td>{{ "{:,}".format(r.total_tokens) }}</td>
          <td>${{ "%.6f"|format(r.estimated_cost) }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Per-category bar chart -->
  <div class="section">
    <h2>Score Comparison</h2>
    <canvas id="catChart_{{ loop.index }}" height="80"></canvas>
  </div>

  <!-- Task-level breakdown -->
  <div class="section">
    <h2>Task-Level Results</h2>
    <table>
      <thead><tr><th>Task</th>{% for r in category_leaderboards[cat] %}<th>{{ r.model }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for tid in task_ids_per_cat.get(cat, []) %}
        <tr>
          <td style="font-weight:600;font-size:.85rem">{{ tid }}</td>
          {% for r in category_leaderboards[cat] %}
            {% set ts = task_score_map.get(cat, {}).get(r.model, {}).get(tid, None) %}
            {% if ts is not none %}
              <td class="{{ 'high' if ts >= 80 else ('mid' if ts >= 60 else ('med' if ts >= 40 else 'low')) }}" style="font-weight:600">{{ "%.0f"|format(ts) }}</td>
            {% else %}
              <td style="color:var(--muted)">—</td>
            {% endif %}
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endfor %}

<!-- ==================== COMPARE TAB ==================== -->
<div id="tab_compare" class="tab-content">
  <h2 style="font-size:1.5rem;margin-bottom:1.5rem">Model Comparison</h2>

  <div class="chart-grid">
    <div class="chart-box full">
      <h3>Radar: All Models Across All Categories</h3>
      <canvas id="radarChart"></canvas>
    </div>
    <div class="chart-box">
      <h3>Overall Average Score</h3>
      <canvas id="overallBarChart"></canvas>
    </div>
    <div class="chart-box">
      <h3>Average Latency (seconds)</h3>
      <canvas id="latencyChart"></canvas>
    </div>
    <div class="chart-box">
      <h3>Estimated Cost ($)</h3>
      <canvas id="costChart"></canvas>
    </div>
    <div class="chart-box">
      <h3>Score vs Cost (Efficiency)</h3>
      <canvas id="effChart"></canvas>
    </div>
  </div>

  <!-- Full comparison matrix -->
  <div class="section">
    <h2>Full Score Matrix</h2>
    <div style="overflow-x:auto">
    <table id="matrixTable">
      <thead><tr>
        <th onclick="sortTbl('matrixTable',0)">Category</th>
        {% for m in models %}<th onclick="sortTbl('matrixTable',{{ loop.index }})">{{ m }}</th>{% endfor %}
        <th>Best</th>
      </tr></thead>
      <tbody>
        {% for cat in categories %}
        <tr>
          <td style="font-weight:600">{{ cat }}</td>
          {% for m in models %}
            {% set sc = score_map.get(cat, {}).get(m, None) %}
            {% if sc is not none %}
              <td class="{{ 'high' if sc >= 80 else ('mid' if sc >= 60 else ('med' if sc >= 40 else 'low')) }}" style="font-weight:700">{{ "%.1f"|format(sc) }}</td>
            {% else %}
              <td style="color:var(--muted)">—</td>
            {% endif %}
          {% endfor %}
          <td>{% if best_per_cat.get(cat) %}<span class="best-pill">{{ best_per_cat[cat].model }}</span>{% endif %}</td>
        </tr>
        {% endfor %}
        <tr style="border-top:2px solid var(--accent)">
          <td style="font-weight:800">AVERAGE</td>
          {% for m in models %}
          <td style="font-weight:800;color:var(--accent)">{{ "%.1f"|format(model_stats[m].avg_score) }}</td>
          {% endfor %}
          <td><span class="best-pill">{{ overall_winner.model }}</span></td>
        </tr>
      </tbody>
    </table>
    </div>
  </div>
</div>

</div><!-- /container -->

<script>
/* Tab switching */
function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab_' + id).classList.add('active');
  const tabs = document.querySelectorAll('.nav-tab');
  const names = ['overview', ...{{ categories_json }}.map((_,i)=>'cat_'+(i+1)), 'compare'];
  names.forEach((n,i) => { if(n===id) tabs[i]?.classList.add('active'); });
}

/* Table sorting */
function sortTbl(id,col){
  const t=document.getElementById(id),b=t.querySelector('tbody'),rows=Array.from(b.querySelectorAll('tr'));
  const d=t.dataset.sd==='a'?'d':'a';t.dataset.sd=d;
  rows.sort((a,b)=>{let av=a.cells[col]?.textContent.trim().replace(/[$,]/g,''),bv=b.cells[col]?.textContent.trim().replace(/[$,]/g,'');
    let an=parseFloat(av),bn=parseFloat(bv);if(!isNaN(an)&&!isNaN(bn))return d==='a'?an-bn:bn-an;return d==='a'?av.localeCompare(bv):bv.localeCompare(av);});
  rows.forEach(r=>b.appendChild(r));
}

/* Chart colors */
const C=['#3b82f6','#22c55e','#eab308','#ef4444','#a855f7','#f97316','#06b6d4','#84cc16','#ec4899','#6366f1','#fb923c','#14b8a6'];
const CB=C.map(c=>c+'33');
const cf={color:'#a1a1aa'};const gc='#27272a';

/* Radar */
new Chart(document.getElementById('radarChart'),{type:'radar',data:{labels:{{ categories_json }},datasets:{{ radar_json }}},
  options:{responsive:true,scales:{r:{min:0,max:100,ticks:cf,grid:{color:gc},pointLabels:{color:'#fafafa',font:{size:11}}}},plugins:{legend:{labels:{color:'#fafafa'}}}}});

/* Overall bar */
new Chart(document.getElementById('overallBarChart'),{type:'bar',data:{labels:{{ models_json }},datasets:[{label:'Avg Score',data:{{ avg_scores_json }},backgroundColor:C.slice(0,{{ num_models }}),borderWidth:0,borderRadius:4}]},
  options:{indexAxis:'y',responsive:true,scales:{x:{min:0,max:100,ticks:cf,grid:{color:gc}},y:{ticks:{color:'#fafafa'}}},plugins:{legend:{display:false}}}});

/* Latency */
new Chart(document.getElementById('latencyChart'),{type:'bar',data:{labels:{{ models_json }},datasets:[{label:'Avg Latency (s)',data:{{ latencies_json }},backgroundColor:'#eab308',borderWidth:0,borderRadius:4}]},
  options:{responsive:true,scales:{y:{ticks:cf,grid:{color:gc}},x:{ticks:{color:'#fafafa'}}},plugins:{legend:{display:false}}}});

/* Cost */
new Chart(document.getElementById('costChart'),{type:'bar',data:{labels:{{ models_json }},datasets:[{label:'Cost ($)',data:{{ costs_json }},backgroundColor:'#ef4444',borderWidth:0,borderRadius:4}]},
  options:{responsive:true,scales:{y:{ticks:cf,grid:{color:gc}},x:{ticks:{color:'#fafafa'}}},plugins:{legend:{display:false}}}});

/* Efficiency scatter */
new Chart(document.getElementById('effChart'),{type:'scatter',data:{datasets:{{ eff_json }}},
  options:{responsive:true,scales:{x:{title:{display:true,text:'Cost ($)',color:'#fafafa'},ticks:cf,grid:{color:gc}},y:{title:{display:true,text:'Avg Score',color:'#fafafa'},min:0,max:100,ticks:cf,grid:{color:gc}}},plugins:{legend:{labels:{color:'#fafafa'}}}}});

/* Per-category bar charts */
{% for cat in categories %}
(function(){
  const lb={{ category_leaderboards_json[cat] }};
  new Chart(document.getElementById('catChart_{{ loop.index }}'),{type:'bar',
    data:{labels:lb.map(r=>r.model),datasets:[{label:'Score',data:lb.map(r=>r.score),backgroundColor:C.slice(0,lb.length),borderWidth:0,borderRadius:4}]},
    options:{responsive:true,scales:{y:{min:0,max:100,ticks:cf,grid:{color:gc}},x:{ticks:{color:'#fafafa'}}},plugins:{legend:{display:false}}}});
})();
{% endfor %}
</script>
</body>
</html>
"""

CHART_COLORS = [
    "#3b82f6", "#22c55e", "#eab308", "#ef4444", "#a855f7",
    "#f97316", "#06b6d4", "#84cc16", "#ec4899", "#6366f1",
    "#fb923c", "#14b8a6",
]


def generate_html_report(
    results: list[BenchmarkResult],
    output_path: str | None = None,
) -> str:
    """Generate an HTML dashboard report. Returns the file path."""
    if not output_path:
        os.makedirs(settings.RESULTS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(settings.RESULTS_DIR, f"benchmark_report_{ts}.html")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    models = sorted(set(r.model for r in results))
    categories = sorted(set(r.category for r in results))

    # Score map: category -> model -> score
    score_map: dict[str, dict[str, float]] = {}
    for r in results:
        score_map.setdefault(r.category, {})[r.model] = r.avg_score

    # Best per category
    best_per_cat: dict[str, BenchmarkResult] = {}
    for cat in categories:
        cr = [r for r in results if r.category == cat]
        if cr:
            best_per_cat[cat] = max(cr, key=lambda x: x.avg_score)

    # Per-model aggregate stats
    model_stats: dict[str, dict] = {}
    for m in models:
        mrs = [r for r in results if r.model == m]
        avg_sc = sum(r.avg_score for r in mrs) / len(mrs)
        total_cost = sum(r.estimated_cost for r in mrs)
        model_stats[m] = {
            "avg_score": avg_sc,
            "avg_latency": sum(r.avg_latency for r in mrs) / len(mrs),
            "total_tokens": sum(r.total_tokens for r in mrs),
            "total_cost": total_cost,
            "efficiency": avg_sc / total_cost if total_cost > 0 else 0,
        }

    # Overall leaderboard (sorted by avg_score desc)
    overall_lb = sorted(
        [{"model": m, **model_stats[m]} for m in models],
        key=lambda x: x["avg_score"], reverse=True,
    )

    winner_model = overall_lb[0]["model"] if overall_lb else "N/A"
    overall_winner = type("W", (), {
        "model": winner_model,
        "avg_score": model_stats.get(winner_model, {}).get("avg_score", 0),
        "avg_latency": model_stats.get(winner_model, {}).get("avg_latency", 0),
    })()

    # Per-category leaderboards
    category_leaderboards: dict[str, list[BenchmarkResult]] = {}
    category_leaderboards_json: dict[str, str] = {}
    for cat in categories:
        cr = sorted(
            [r for r in results if r.category == cat],
            key=lambda x: x.avg_score, reverse=True,
        )
        category_leaderboards[cat] = cr
        category_leaderboards_json[cat] = json.dumps([
            {"model": r.model, "score": r.avg_score} for r in cr
        ])

    # Category descriptions and task counts
    from benchmarks.registry import ALL_BENCHMARKS
    cat_desc_map = {b.category: b.description for b in ALL_BENCHMARKS}
    cat_task_counts: dict[str, int] = {}
    for cat in categories:
        for b in ALL_BENCHMARKS:
            if b.category == cat:
                cat_task_counts[cat] = len(b.get_tasks())
                break

    # Task-level score map: cat -> model -> task_id -> score
    task_score_map: dict[str, dict[str, dict[str, float]]] = {}
    task_ids_per_cat: dict[str, list[str]] = {}
    for r in results:
        cat_m = task_score_map.setdefault(r.category, {})
        m_tasks = cat_m.setdefault(r.model, {})
        for tr in r.task_results:
            m_tasks[tr.task_id] = tr.score
            if r.category not in task_ids_per_cat:
                task_ids_per_cat[r.category] = []
            if tr.task_id not in task_ids_per_cat[r.category]:
                task_ids_per_cat[r.category].append(tr.task_id)

    # Radar datasets
    radar_ds = []
    for i, m in enumerate(models):
        c = CHART_COLORS[i % len(CHART_COLORS)]
        radar_ds.append({
            "label": m,
            "data": [score_map.get(cat, {}).get(m, 0) for cat in categories],
            "backgroundColor": c + "22",
            "borderColor": c,
            "borderWidth": 2,
            "pointRadius": 3,
        })

    # Efficiency scatter
    eff_ds = []
    for i, m in enumerate(models):
        c = CHART_COLORS[i % len(CHART_COLORS)]
        eff_ds.append({
            "label": m,
            "data": [{"x": round(model_stats[m]["total_cost"], 6), "y": round(model_stats[m]["avg_score"], 1)}],
            "backgroundColor": c,
            "pointRadius": 10,
            "pointHoverRadius": 14,
        })

    total_tasks_run = sum(len(r.task_results) for r in results)
    total_tokens_all = sum(r.total_tokens for r in results)
    total_cost_all = round(sum(r.estimated_cost for r in results), 4)

    template = Template(HTML_TEMPLATE)
    html = template.render(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        num_models=len(models),
        num_categories=len(categories),
        total_tasks=total_tasks_run,
        total_tokens_all=f"{total_tokens_all:,}",
        total_cost_all=f"{total_cost_all:.4f}",
        overall_winner=overall_winner,
        overall_leaderboard=overall_lb,
        models=models,
        categories=categories,
        score_map=score_map,
        best_per_cat=best_per_cat,
        model_stats=model_stats,
        category_leaderboards=category_leaderboards,
        category_leaderboards_json=category_leaderboards_json,
        category_descriptions=cat_desc_map,
        category_task_counts=cat_task_counts,
        task_score_map=task_score_map,
        task_ids_per_cat=task_ids_per_cat,
        categories_json=json.dumps(categories),
        models_json=json.dumps(models),
        radar_json=json.dumps(radar_ds),
        avg_scores_json=json.dumps([round(model_stats[m]["avg_score"], 1) for m in models]),
        latencies_json=json.dumps([round(model_stats[m]["avg_latency"], 2) for m in models]),
        costs_json=json.dumps([round(model_stats[m]["total_cost"], 6) for m in models]),
        eff_json=json.dumps(eff_ds),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
