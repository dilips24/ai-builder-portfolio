"""Streamlit UI for the Change Request FAQ Agent (rules first, Haiku fallback).

Run from the change-request-faq-agent folder:  streamlit run day05\\app.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "day04"))
import router  # noqa: E402  (needs day04 on sys.path)

EXAMPLE_FILES = [ROOT / "day03" / "faqs.json", ROOT / "day04" / "holdout.json"]
NO_EXAMPLE = "— type your own —"
BADGES = {"rule": "⚡ Rule", "llm": "🤖 AI (Haiku)"}


@st.cache_resource
def get_rules():
    return router.load_rules()


@st.cache_resource
def get_policy():
    return router.load_policy()


@st.cache_resource
def get_llm_client():
    return router.get_client()


@st.cache_data
def load_examples() -> dict[str, str]:
    examples = {}
    for path in EXAMPLE_FILES:
        for item in json.loads(path.read_text(encoding="utf-8")):
            q = item["question"]
            short = q if len(q) <= 90 else q[:87] + "..."
            examples[f"{item['id']} · {short}"] = q
    return examples


def use_example() -> None:
    choice = st.session_state.example
    if choice != NO_EXAMPLE:
        st.session_state.question = load_examples()[choice]


def ask(question: str, rules_off: bool) -> dict | None:
    rules = {} if rules_off else get_rules()  # empty rules -> nothing matches -> LLM
    needs_llm = len(router.match_categories(router.normalize(question), rules)) != 1
    try:
        client = get_llm_client() if needs_llm else None
        return router.route(question, rules, get_policy(), client)
    except SystemExit as e:  # router.py reports missing key / API errors via sys.exit(msg)
        st.error(str(e.code))
        return None


def show_result(result: dict, operator: bool) -> None:
    st.markdown("#### Answer")
    st.write(result["answer"])
    if not operator:
        if result["path"] == "llm":
            st.caption("AI-generated")
        return
    st.markdown(f"**Answered by:** {BADGES[result['path']]}")
    cats = ", ".join(result["matched_categories"]) or "—"
    st.markdown(f"**Matched categories:** {cats}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latency", f"{result['latency_ms']:.0f} ms")
    c2.metric("Input tokens", result["input_tokens"])
    c3.metric("Output tokens", result["output_tokens"])
    c4.metric("Cost", f"${result['cost_usd']:.6f}")


def show_history() -> None:
    history = st.session_state.history
    if not history:
        return
    df = pd.DataFrame(history)
    st.markdown("#### Session history")

    n = len(df)
    rule_share = (df["path"] == BADGES["rule"]).mean()
    avg = df.groupby("path")["latency_ms"].mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("Questions asked", n)
    c2.metric("Answered by rules", f"{rule_share:.0%}")
    c3.metric("Total cost", f"${df['cost_usd'].sum():.6f}")
    c4, c5 = st.columns(2)
    for col, key in ((c4, BADGES["rule"]), (c5, BADGES["llm"])):
        value = f"{avg[key]:.0f} ms" if key in avg else "n/a"
        col.metric(f"Avg latency · {key}", value)

    st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")


st.set_page_config(page_title="Change Request FAQ Agent", page_icon="📋", layout="wide")
if "history" not in st.session_state:
    st.session_state.history = []
    st.session_state.question = ""
    st.session_state.last_result = None

with st.sidebar:
    st.header("Settings")
    rules_off = st.toggle("Send everything to AI (rules off)")
    operator = st.toggle("Show operator details", value=True)
    if rules_off:
        st.caption("Rules are bypassed, so matched categories will be empty.")
    if st.button("Clear history"):
        st.session_state.history = []
        st.session_state.last_result = None
        st.rerun()
    st.caption(f"Model: {router.MODEL}")

st.title("Change Request FAQ Agent")
st.write(
    "Ask a change-management question: keyword rules answer known questions instantly, "
    "and anything else goes to the AI."
)

st.selectbox(
    "Example questions",
    [NO_EXAMPLE, *load_examples()],
    key="example",
    on_change=use_example,
)

with st.form("ask"):
    st.text_input("Your question", key="question")
    submitted = st.form_submit_button("Ask")

if submitted:
    question = st.session_state.question.strip()
    if not question:
        st.warning("Type a question first.")
    else:
        with st.spinner("Thinking..."):
            result = ask(question, rules_off)
        st.session_state.last_result = result
        if result:
            st.session_state.history.append(
                {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "question": question,
                    "path": BADGES[result["path"]],
                    "categories": ", ".join(result["matched_categories"]) or "—",
                    "latency_ms": round(result["latency_ms"]),
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "cost_usd": round(result["cost_usd"], 6),
                    "rules_off": rules_off,
                }
            )

if st.session_state.last_result:
    show_result(st.session_state.last_result, operator)
if operator:
    show_history()
