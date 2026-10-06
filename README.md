# Company Policy Assistant

A comparison of rules-based search, an LLM with the full policy database, and an LLM with vector retrieval. The website displays saved measurements from all three methods on ten questions and includes exactly two comparison paragraphs and two tables.

## Website

Public website: https://sara-cairati-company-policy-assistant.streamlit.app/

Deploy `streamlit_app.py` on Streamlit Community Cloud using Python 3.12. The website needs no API key: it reads the saved results. Choose this repository, branch `main`, and main file `streamlit_app.py`.

## Run locally

```sh
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## Reproduce the comparison

Create a local `.env` file containing `GEMINI_API_KEY=your_key`, then run:

```sh
python compare_methods.py
```

This makes paid or quota-limited API requests according to your Gemini plan. It overwrites saved measurements and resets manual review fields. Keep the reviewed submission results if you need to preserve them. Generation uses Gemini 3.8 Flash with Gemini 3.5 Flash Lite as fallback; daily-quota failures skip later calls to the exhausted model in that run. Vector retrieval uses Gemini Embedding 2 and one closest policy from the saved embeddings. First and last index entries are checked for model and order compatibility before the run.

## Results and review

- `comparison_results.json` and `.csv`: 30 actual answers with policies, response times, generation tokens and review notes.
- `comparison_summary.json`: aggregate accuracy, latency and token use.
- `comparison_explanation.md`: exactly two paragraphs explaining the findings and preferred approach.
- `company_policies.csv`: 98 source policies.
- `policy_embeddings.json`: saved policy embeddings; offline construction is excluded from query measurements.
- `test_questions.txt`: ten fixed questions, including three absent from the policy database.

Current reviewed run: rules-based search 4/10 correct; both LLM methods 10/10. All answers were read against the policy database. Five keyword answers quote an unrelated policy; no invented policy statements were found in this sample. Generation tokens exclude failed-call usage. Embedding tokens were not reported by the API. Timing includes retries, so these results are not a controlled speed benchmark or a general hallucination-rate estimate.

## Credentials

Never upload `.env`, `.streamlit/secrets.toml`, or API tokens. The published website does not make live Gemini calls.

## Assignment status

The comparison website is deployed. The Slack bot is implemented and has answered a live dress-code question in the separate Sara Cairati — Company Policy Assistant workspace, channel sara-cairati-policy-testing. See SLACK_SETUP.md for running it locally. Instructor invitation and submission screenshot are still pending.
