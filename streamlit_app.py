"""Assignment comparison website. Uses saved measurements; no API key is needed."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
NAMES = {
    "rules": "Rules-based search",
    "llm_no_vector": "LLM without vectors",
    "llm_vector": "LLM with vectors",
}

st.set_page_config(page_title="Company Policy Assistant", page_icon="📋", layout="wide")
st.title("Company Policy Assistant")
st.caption("Sara Cairati · Three approaches · 98 policies · 10 questions · 6 October 2026")

try:
    report = json.loads((BASE_DIR / "comparison_results.json").read_text(encoding="utf-8"))
    paragraphs = (BASE_DIR / "comparison_explanation.md").read_text(encoding="utf-8").strip().split("\n\n")
    if len(paragraphs) != 2:
        raise ValueError("The comparison explanation must contain exactly two paragraphs.")
except (OSError, ValueError) as error:
    st.error(f"Unable to load the saved comparison: {error}")
    st.stop()

st.subheader("Results at a glance")
summary_rows = []
for result in report["summary"]:
    summary_rows.append({
        "Approach": NAMES[result["method"]],
        "Correct answers": f"{result['correct_answers']}/10",
        "Mean response time (s)": result["mean_response_seconds"],
        "Generation tokens (10 questions)": result["generation_total_tokens"],
        "Unrelated policies cited": result["incorrect_policy_attributions"],
        "Invented policy claims": result["unsupported_claims"],
    })
st.dataframe(pd.DataFrame(summary_rows), hide_index=True, width="stretch",
             column_config={"Mean response time (s)": st.column_config.NumberColumn(format="%.5f")})

st.subheader("Comparison and preferred approach")
for paragraph in paragraphs:
    st.markdown(paragraph)

st.subheader("Every question, every answer")
answer_rows = []
for result in report["results"]:
    answer_rows.append({
        "Question": f"Q{result['question_number']}: {result['question']}",
        "Approach": NAMES[result["method"]],
        "Answer": result["answer"],
        "Relevant policy": result["relevant_policy"] or "None",
        "Response time (s)": result["response_time"],
        "Input tokens": result["input_tokens"],
        "Output tokens": result["output_tokens"],
        "Total generation tokens": result["total_tokens"],
        "Embedding tokens": str(result["embedding_tokens"]) if result["embedding_tokens"] is not None else "Not reported",
        "Correct": "Yes" if result["correct"] else "No",
        "Invented claims": "Yes" if result.get("unsupported_claim") else "No",
        "Assessment": result["assessment_note"],
    })
st.dataframe(pd.DataFrame(answer_rows), hide_index=True, width="stretch", height=650,
             column_config={
                 "Answer": st.column_config.TextColumn(width="large"),
                 "Question": st.column_config.TextColumn(width="large"),
                 "Assessment": st.column_config.TextColumn(width="large"),
                 "Response time (s)": st.column_config.NumberColumn(format="%.5f"),
             })

st.subheader("Measurement notes")
st.caption("Both LLM approaches used Gemini 3.5 Flash Lite after the primary model exhausted its daily quota. Timing includes embedding, retrieval, generation and retries where applicable; Q9 was affected by minute-rate limits.")
st.caption("Vector retrieval uses Gemini Embedding 2 and the single closest policy from the saved 3,072-dimensional index. Its first and last entries were verified against the current embedding model.")
st.caption("Generation tokens are from successful responses. Embedding tokens were not reported by the API. Failed-request usage and offline index construction are excluded.")
st.caption("All 30 answers were manually reviewed against the database. A true quotation from an unrelated policy is still an incorrect answer. This ten-question sample does not establish a general hallucination rate.")

left, middle, right = st.columns(3)
with left:
    st.download_button("Download results (CSV)", (BASE_DIR / "comparison_results.csv").read_bytes(),
                       file_name="comparison_results.csv", mime="text/csv")
with middle:
    st.download_button("Download full measurements (JSON)", (BASE_DIR / "comparison_results.json").read_bytes(),
                       file_name="comparison_results.json", mime="application/json")
with right:
    st.download_button("Download two-paragraph comparison", (BASE_DIR / "comparison_explanation.md").read_bytes(),
                       file_name="comparison_explanation.md", mime="text/markdown")
