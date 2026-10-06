"""Compare three policy-answering approaches and save reproducible measurements."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from google import genai

BASE_DIR = Path(__file__).resolve().parent
MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite")
EMBEDDING_MODEL = "gemini-embedding-2"
METHODS = ("rules", "llm_no_vector", "llm_vector")
client = None
policies = []
policy_embeddings = []
exhausted_models = set()


def initialize():
    global client, policies, policy_embeddings
    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from the environment or .env file.")
    client = genai.Client(api_key=api_key)
    with (BASE_DIR / "company_policies.csv").open(encoding="utf-8") as file:
        policies = list(csv.DictReader(file))
    policy_embeddings = json.loads((BASE_DIR / "policy_embeddings.json").read_text())
    if len(policy_embeddings) != len(policies):
        raise ValueError("Policy and embedding counts do not match.")
    if not policy_embeddings or any(len(v) != 3072 for v in policy_embeddings):
        raise ValueError("Expected one 3072-dimensional embedding per policy.")
    exhausted_models.clear()


def rules_search(question):
    stop_words = {
        "i", "me", "my", "we", "our", "you", "your",
        "a", "an", "the", "is", "are", "am", "be",
        "to", "of", "in", "on", "at", "for", "from",
        "can", "could", "should", "would", "do", "does",
        "what", "when", "where", "how"
    }

    question_words = [
        word for word in question.lower().split()
        if word not in stop_words
    ]

    best_policy = None
    best_score = 0

    for policy in policies:
        searchable_text = (
            policy["title"] + " " +
            policy["department"] + " " +
            policy["category"] + " " +
            policy["policy_text"]
        ).lower()

        score = 0

        for word in question_words:
            if word in searchable_text:
                score += 1

        if score > best_score:
            best_score = score
            best_policy = policy

    return best_policy, best_score

def cosine_similarity(vector_a, vector_b):
    if len(vector_a) != len(vector_b):
        raise ValueError("Embedding dimensions do not match.")
    magnitude = math.sqrt(sum(a * a for a in vector_a) * sum(b * b for b in vector_b))
    if not magnitude:
        raise ValueError("An embedding has zero magnitude.")
    return sum(a * b for a, b in zip(vector_a, vector_b)) / magnitude


def embed(text):
    for attempt in range(3):
        try:
            response = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
            embedding = response.embeddings[0]
            statistics = embedding.statistics
            tokens = statistics.token_count if statistics else None
            return embedding.values, tokens
        except Exception as error:
            if attempt == 2 or daily_quota_exhausted(error):
                raise
            code = getattr(error, "code", None)
            if code is not None and code not in (429, 500, 502, 503, 504):
                raise
            print("Embedding request failed. Retrying in 5 seconds...", flush=True)
            time.sleep(5)


def verify_embedding_index():
    # The legacy cache has no model/source metadata. Verify its endpoints before reuse.
    similarities = []
    for index in (0, len(policies) - 1):
        policy = policies[index]
        text = f"Title: {policy['title']}. Policy: {policy['policy_text']}"
        vector, _ = embed(text)
        similarity = cosine_similarity(vector, policy_embeddings[index])
        similarities.append(similarity)
        if similarity < 0.999:
            raise ValueError("Legacy embeddings do not match the configured model and policy order.")
    return {"model": EMBEDDING_MODEL, "dimensions": 3072,
            "checked_indices": [0, len(policies) - 1], "cosine_similarities": similarities,
            "note": "Legacy cache: first and last entries checked; original build metadata unavailable."}


def daily_quota_exhausted(error):
    return getattr(error, "code", None) == 429 and any(
        marker in str(error).lower() for marker in
        ("requestsperday", "requests_per_day", "tokensperday", "tokens_per_day")
    )


def make_prompt(question, context):
    return f"""You are a company policy assistant.
Answer the employee's question using only the company policies provided below.
Identify the relevant policy by its exact title.
If the policies do not contain enough information, use Relevant policy: None
and explain that the provided policies do not contain enough information.
Do not infer permission or prohibition from an unrelated policy.

COMPANY POLICIES:
{context}

EMPLOYEE QUESTION:
{question}

Return your answer in this format:
Relevant policy: [policy title or None]
Answer: [answer]
"""


def format_policies(selected):
    return "\n\n".join(
        f"Title: {p['title']}\nDepartment: {p['department']}\n"
        f"Category: {p['category']}\nPolicy: {p['policy_text']}"
        for p in selected
    )


def parse_answer(text):
    policy_label, separator, answer = text.partition("Answer:")
    if not separator or not policy_label.strip().startswith("Relevant policy:"):
        raise ValueError("Model response is missing the required answer format.")
    title = policy_label.strip().removeprefix("Relevant policy:").strip()
    return None if title.lower() == "none" else title, answer.strip()


def generate_answer(prompt):
    errors = []
    for model in MODELS:
        if model in exhausted_models:
            continue
        if model != MODELS[0]:
            print(f"Using fallback model: {model}", flush=True)
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                # Read text parts directly so non-text thought signatures are not treated as answers.
                parts = response.candidates[0].content.parts if response.candidates else []
                text = "".join(part.text for part in parts if part.text and not part.thought)
                title, answer = parse_answer(text)
                usage = response.usage_metadata
                return {"answer": answer, "relevant_policy": title, "raw_response": text,
                        "model": model, "input_tokens": getattr(usage, "prompt_token_count", None),
                        "output_tokens": getattr(usage, "candidates_token_count", None),
                        "thinking_tokens": getattr(usage, "thoughts_token_count", None),
                        "total_tokens": getattr(usage, "total_token_count", None),
                        "api_errors": errors, "status": "ok"}
            except Exception as error:
                code = getattr(error, "code", None)
                # Save diagnostic type/code, without persisting credentials or full request details.
                errors.append({"model": model, "attempt": attempt + 1,
                               "type": type(error).__name__, "code": code})
                print(f"{model} attempt {attempt + 1}/3 failed ({type(error).__name__}, code {code}).", flush=True)
                if daily_quota_exhausted(error):
                    exhausted_models.add(model)
                    print("Daily quota exhausted; skipping further calls to this model in this run.", flush=True)
                    break
                if code is not None and code not in (429, 500, 502, 503, 504):
                    break
                if attempt < 2:
                    time.sleep(5)
    return {"answer": "API error: primary and fallback models unavailable.",
            "relevant_policy": None, "model": None, "input_tokens": None,
            "output_tokens": None, "thinking_tokens": None, "total_tokens": None,
            "api_errors": errors, "status": "error"}


def llm_no_vector(question):
    start = time.perf_counter()
    result = generate_answer(make_prompt(question, format_policies(policies)))
    result.update(response_time=time.perf_counter() - start, embedding_tokens=0,
                  embedding_time=0, retrieved_policy=None, similarity=None)
    return result


def llm_vector(question):
    start = time.perf_counter()
    try:
        vector, embedding_tokens = embed(question)
        embedding_time = time.perf_counter() - start
        similarities = [cosine_similarity(vector, saved) for saved in policy_embeddings]
        best_index = max(range(len(similarities)), key=similarities.__getitem__)
        best_policy = policies[best_index]
        result = generate_answer(make_prompt(question, format_policies([best_policy])))
        result.update(embedding_tokens=embedding_tokens, embedding_time=embedding_time,
                      retrieved_policy=best_policy["title"], similarity=similarities[best_index])
    except Exception as error:
        result = {"answer": "Vector retrieval failed.", "relevant_policy": None,
                  "model": None, "input_tokens": None, "output_tokens": None,
                  "thinking_tokens": None, "total_tokens": None, "embedding_tokens": None,
                  "embedding_time": time.perf_counter() - start, "retrieved_policy": None,
                  "similarity": None, "status": "error",
                  "api_errors": [{"type": type(error).__name__, "code": getattr(error, "code", None)}]}
    result["response_time"] = time.perf_counter() - start
    return result


def rules_result(question):
    start = time.perf_counter()
    policy, score = rules_search(question)
    return {"answer": policy["policy_text"] if policy else "No relevant policy found.",
            "relevant_policy": policy["title"] if policy else None,
            "response_time": time.perf_counter() - start, "model": None,
            "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0,
            "total_tokens": 0, "embedding_tokens": 0, "embedding_time": 0,
            "retrieved_policy": policy["title"] if policy else None,
            "similarity": None, "match_score": score, "status": "ok", "api_errors": []}


def save_results(report):
    target = BASE_DIR / "comparison_results.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
    fields = ["question_number", "question", "method", "answer", "relevant_policy",
              "response_time", "model", "input_tokens", "output_tokens", "thinking_tokens",
              "total_tokens", "embedding_tokens", "embedding_time", "retrieved_policy",
              "similarity", "status", "expected_policy", "policy_match", "answer_supported",
              "correct", "assessment_note"]
    with (BASE_DIR / "comparison_results.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["results"])


def main():
    initialize()
    questions = [line.strip() for line in (BASE_DIR / "test_questions.txt").read_text().splitlines() if line.strip()]
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "policy_count": len(policies),
              "policy_database_sha256": hashlib.sha256((BASE_DIR / "company_policies.csv").read_bytes()).hexdigest(),
              "generation_models": list(MODELS), "embedding_model": EMBEDDING_MODEL,
              "retrieval_top_k": 1, "question_count": len(questions),
              "measurement_notes": ["Response time includes query embedding, retrieval, generation and retries where applicable.",
                                    "Generation tokens come from the successful response; failed-request usage is unavailable.",
                                    "Embedding tokens are reported separately; null means the API did not report them.",
                                    "Offline policy-index construction cost is excluded from per-question measurements.",
                                    "Answer support and correctness require manual review against all policies; null means unreviewed.",
                                    "One run of ten questions does not establish a general hallucination rate."],
              "results": []}
    report["embedding_index_validation"] = verify_embedding_index()
    print(f"Comparing all three methods on {len(questions)} questions.", flush=True)
    for number, question in enumerate(questions, start=1):
        print(f"\nQuestion {number}: {question}", flush=True)
        for method, function in (("rules", rules_result), ("llm_no_vector", llm_no_vector), ("llm_vector", llm_vector)):
            result = function(question)
            result.update(question_number=number, question=question, method=method,
                          expected_policy=None, policy_match=None, answer_supported=None,
                          correct=None, assessment_note="Pending manual review.")
            report["results"].append(result)
            save_results(report)
            print(f"{method}: {result['relevant_policy']} | {result['answer']} | {result['response_time']:.3f}s", flush=True)
    print("\nSaved comparison_results.json and comparison_results.csv.", flush=True)


if __name__ == "__main__":
    main()
