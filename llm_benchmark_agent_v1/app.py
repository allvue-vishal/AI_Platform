"""Streamlit dashboard for the LLM Benchmark Agent.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import settings, CATEGORY_META
from benchmarks.registry import ALL_BENCHMARKS, get_all_categories

# ──────────────────────────────────────────────────────────────────
#  Page config
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LLM Benchmark",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_results(results_dir: str) -> list[dict]:
    """Load all JSON result files from the results directory."""
    results = []
    if not os.path.isdir(results_dir):
        return results
    for fname in sorted(os.listdir(results_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(results_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append(data)
        except Exception:
            continue
    return results


def results_to_df(results: list[dict]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame()
    rows = []
    for r in results:
        rows.append({
            "model": r.get("model", ""),
            "category": r.get("category", ""),
            "benchmark_name": r.get("benchmark_name", ""),
            "avg_score": r.get("avg_score", 0),
            "avg_latency": r.get("avg_latency", 0),
            "total_tokens": r.get("total_tokens", 0),
            "total_prompt_tokens": r.get("total_prompt_tokens", 0),
            "total_completion_tokens": r.get("total_completion_tokens", 0),
            "estimated_cost": r.get("estimated_cost", 0),
            "timestamp": r.get("timestamp", ""),
            "num_tasks": len(r.get("task_results", [])),
        })
    return pd.DataFrame(rows)


def get_task_df(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        model = r.get("model", "")
        category = r.get("category", "")
        for tr in r.get("task_results", []):
            rows.append({
                "model": model,
                "category": category,
                "task_id": tr.get("task_id", ""),
                "score": tr.get("score", 0),
                "latency_seconds": tr.get("latency_seconds", 0),
                "prompt_tokens": tr.get("prompt_tokens", 0),
                "completion_tokens": tr.get("completion_tokens", 0),
                "total_tokens": tr.get("total_tokens", 0),
                "error": tr.get("error"),
            })
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────
#  Sidebar navigation
# ──────────────────────────────────────────────────────────────────
st.sidebar.title("LLM Benchmark")
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Run Benchmarks", "Category Details", "Public Comparison"],
    index=0,
)

results_dir = st.sidebar.text_input("Results directory", value=settings.RESULTS_DIR)
raw_results = load_results(results_dir)
df = results_to_df(raw_results)

st.sidebar.markdown("---")
st.sidebar.caption(f"Loaded **{len(raw_results)}** result files")

# ──────────────────────────────────────────────────────────────────
#  PAGE 1: Dashboard
# ──────────────────────────────────────────────────────────────────
if page == "Dashboard":
    st.title("LLM Benchmark Dashboard")

    if df.empty:
        st.warning("No benchmark results found. Run benchmarks first or check the results directory path.")
        st.stop()

    # Best model callout
    model_avg = (
        df.groupby("model")
        .agg(score=("avg_score", "mean"), latency=("avg_latency", "mean"))
        .sort_values("score", ascending=False)
        .reset_index()
    )
    best = model_avg.iloc[0]
    st.success(
        f"**Best Model: {best['model']}** — "
        f"Score **{best['score']:.1f}**/100 — "
        f"Avg latency **{best['latency']:.2f}s**"
    )

    st.markdown("---")

    # Model leaderboard table
    st.subheader("Model Leaderboard")
    leaderboard = model_avg.copy()
    leaderboard.insert(0, "Rank", range(1, len(leaderboard) + 1))
    leaderboard.columns = ["Rank", "Model", "Score", "Avg Latency (s)"]
    leaderboard["Score"] = leaderboard["Score"].round(1)
    leaderboard["Avg Latency (s)"] = leaderboard["Avg Latency (s)"].round(2)
    st.dataframe(leaderboard, width="stretch", hide_index=True)

    st.markdown("---")

    # Score by model bar chart
    st.subheader("Overall Score by Model")
    fig_bar = px.bar(
        model_avg.sort_values("score", ascending=True),
        x="score",
        y="model",
        orientation="h",
        color="score",
        color_continuous_scale="RdYlGn",
        labels={"score": "Average Score", "model": "Model"},
    )
    fig_bar.update_layout(showlegend=False, height=max(300, 50 * len(model_avg)))
    st.plotly_chart(fig_bar, width="stretch")


# ──────────────────────────────────────────────────────────────────
#  PAGE 2: Run Benchmarks
# ──────────────────────────────────────────────────────────────────
elif page == "Run Benchmarks":
    st.title("Run Benchmarks")
    st.info(
        "Use the CLI to run benchmarks against your LiteLLM proxy. "
        "Results are saved to the results directory and picked up by this dashboard automatically."
    )

    st.subheader("Available Benchmark Categories")
    cat_data = []
    for b in ALL_BENCHMARKS:
        tasks = b.get_tasks()
        slug = b.category.lower().replace(" ", "_").replace("/", "_")
        meta = CATEGORY_META.get(slug, {})
        cat_data.append({
            "Category": b.category,
            "Description": b.description,
            "Tasks": len(tasks),
        })
    st.dataframe(pd.DataFrame(cat_data), width="stretch", hide_index=True)

    st.subheader("CLI Quick Reference")
    st.code(
        "# Run all benchmarks on all discovered models\n"
        "python main.py run\n\n"
        "# Run specific categories\n"
        "python main.py run -c reasoning,math\n\n"
        "# Run specific models\n"
        "python main.py benchmark -m gpt-4o,claude-sonnet-4-5\n\n"
        "# List available models\n"
        "python main.py models\n\n"
        "# List categories\n"
        "python main.py categories",
        language="bash",
    )

    st.subheader("Proxy Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("LiteLLM Proxy URL", value=settings.LITELLM_PROXY_URL, disabled=True)
    with col2:
        st.text_input("Judge Model", value=settings.JUDGE_MODEL, disabled=True)


# ──────────────────────────────────────────────────────────────────
#  PAGE 3: Category Details
# ──────────────────────────────────────────────────────────────────
elif page == "Category Details":
    st.title("Category Details")

    if df.empty:
        st.warning("No results found.")
        st.stop()

    categories = sorted(df["category"].unique())
    selected_cat = st.selectbox("Select category", categories)

    cat_df = df[df["category"] == selected_cat]
    task_df = get_task_df(raw_results)
    cat_task_df = task_df[task_df["category"] == selected_cat]

    st.subheader(f"Model comparison — {selected_cat}")

    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(
            cat_df.sort_values("avg_score", ascending=True),
            x="avg_score",
            y="model",
            orientation="h",
            color="avg_score",
            color_continuous_scale="RdYlGn",
            labels={"avg_score": "Score", "model": "Model"},
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, width="stretch")

    with col2:
        fig_lat = px.bar(
            cat_df.sort_values("avg_latency", ascending=True),
            x="avg_latency",
            y="model",
            orientation="h",
            color="avg_latency",
            color_continuous_scale="Blues",
            labels={"avg_latency": "Latency (s)", "model": "Model"},
        )
        fig_lat.update_layout(showlegend=False)
        st.plotly_chart(fig_lat, width="stretch")

    if not cat_task_df.empty:
        st.subheader("Per-task breakdown")

        fig_task = px.bar(
            cat_task_df,
            x="task_id",
            y="score",
            color="model",
            barmode="group",
            labels={"score": "Score", "task_id": "Task ID"},
        )
        st.plotly_chart(fig_task, width="stretch")

        with st.expander("Task-level data"):
            st.dataframe(cat_task_df, width="stretch", hide_index=True)


# ──────────────────────────────────────────────────────────────────
#  PAGE 4: Public Comparison
# ──────────────────────────────────────────────────────────────────
elif page == "Public Comparison":
    st.title("Public Benchmark Comparison")
    st.markdown(
        "Compare your custom benchmark scores with public benchmark results "
        "from the Open LLM Leaderboard."
    )

    from leaderboard.public_scores import fetch_hf_leaderboard, get_comparison_df, match_model_to_public

    with st.spinner("Fetching public leaderboard data..."):
        public_df = fetch_hf_leaderboard()

    st.subheader("Public Leaderboard Scores")
    st.dataframe(public_df, width="stretch", hide_index=True)

    if df.empty:
        st.warning("No local results to compare. Run benchmarks first.")
        st.stop()

    st.markdown("---")
    st.subheader("Side-by-Side Comparison")

    local_records = df[["model", "category", "avg_score"]].to_dict("records")
    comparison_df = get_comparison_df(local_records)

    if not comparison_df.empty:
        st.dataframe(comparison_df, width="stretch", hide_index=True)

        st.subheader("Custom vs Public Scores")

        local_avg = df.groupby("model")["avg_score"].mean().reset_index()
        local_avg.columns = ["model", "Custom Benchmark"]
        local_avg["Public Match"] = local_avg["model"].apply(match_model_to_public)

        public_avg = public_df[["model_name", "average"]].copy()
        public_avg.columns = ["Public Match", "Public Average"]

        merged = local_avg.merge(public_avg, on="Public Match", how="left")
        merged = merged.dropna(subset=["Public Average"])

        if not merged.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Custom Benchmark",
                x=merged["model"],
                y=merged["Custom Benchmark"],
                marker_color="#636EFA",
            ))
            fig.add_trace(go.Bar(
                name="Public Benchmark Average",
                x=merged["model"],
                y=merged["Public Average"],
                marker_color="#EF553B",
            ))
            fig.update_layout(
                barmode="group",
                yaxis_title="Score",
                xaxis_title="Model",
                height=500,
            )
            st.plotly_chart(fig, width="stretch")

            st.subheader("Performance Gap Analysis")
            merged["Gap"] = merged["Custom Benchmark"] - merged["Public Average"]
            fig_gap = px.bar(
                merged.sort_values("Gap"),
                x="Gap",
                y="model",
                orientation="h",
                color="Gap",
                color_continuous_scale="RdYlGn",
                labels={"Gap": "Custom - Public Score", "model": "Model"},
            )
            fig_gap.update_layout(height=max(300, 60 * len(merged)))
            st.plotly_chart(fig_gap, width="stretch")

            st.caption(
                "A positive gap means the model scores higher on your custom benchmarks "
                "than on public general benchmarks. A negative gap suggests the model is weaker "
                "on domain-specific tasks."
            )
        else:
            st.info("No matching models found between local results and public leaderboard.")
    else:
        st.info("Could not generate comparison table.")
