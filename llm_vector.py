import os
import csv
import json
import math
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

with open("company_policies.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    policies = list(reader)

policy_texts = []

for policy in policies:
    text = (
        f"Title: {policy['title']}. "
        f"Policy: {policy['policy_text']}"
    )
    policy_texts.append(text)

print(f"Prepared {len(policy_texts)} policies for embedding.")
print(policy_texts[0])

with open("policy_embeddings.json", "r", encoding="utf-8") as file:
    policy_embeddings = json.load(file)

print(f"Loaded embeddings for {len(policy_embeddings)} policies.")
print(f"Each embedding has {len(policy_embeddings[0])} dimensions.")

question = input("\nAsk a policy question: ")

start_time = time.time()

question_result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=question
)

question_embedding = question_result.embeddings[0].values

print(f"Question embedding created with {len(question_embedding)} dimensions.")

def cosine_similarity(vector_a, vector_b):
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    return dot_product / (magnitude_a * magnitude_b)


similarities = []

for policy_embedding in policy_embeddings:
    similarity = cosine_similarity(question_embedding, policy_embedding)
    similarities.append(similarity)

best_index = similarities.index(max(similarities))
best_policy = policies[best_index]

print("\nClosest policy:", best_policy["title"])
print("Policy text:", best_policy["policy_text"])
print(f"Similarity score: {similarities[best_index]:.4f}")

prompt = f"""
You are a company policy assistant.

Answer the employee's question using only the policy provided below.
Do not use information that is not supported by this policy.

Relevant policy: {best_policy['title']}
Policy text: {best_policy['policy_text']}

Employee question:
{question}

Return your answer in this format:
Relevant policy: [policy title]
Answer: [answer]
"""

max_attempts = 3

for attempt in range(max_attempts):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        print("\nLLM answer:")
        print(response.text)

        end_time = time.time()
        response_time = end_time - start_time

        print(f"\nResponse time: {response_time:.2f} seconds")
        
        if response.usage_metadata:
            print("Input tokens:", response.usage_metadata.prompt_token_count)
            print("Output tokens:", response.usage_metadata.candidates_token_count)
            print("Total tokens:", response.usage_metadata.total_token_count)        

        break

    except Exception as error:
        if "503" in str(error) and attempt < max_attempts - 1:
            print("Gemini is busy. Retrying in 5 seconds...")
            time.sleep(5)
        else:
            print("\nUnable to get a response from Gemini.")
            print("Error:", error)
