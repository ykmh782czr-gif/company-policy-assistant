import os
import csv
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

with open("company_policies.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    policies = list(reader)

policy_database = ""

for policy in policies:
    policy_database += (
        f"Title: {policy['title']}\n"
        f"Department: {policy['department']}\n"
        f"Category: {policy['category']}\n"
        f"Policy: {policy['policy_text']}\n\n"
    )

print(f"Prepared {len(policies)} policies for the LLM.")

question = input("Ask a policy question: ")

prompt = f"""
You are a company policy assistant.

Answer the employee's question using only the company policies provided below.
Identify the relevant policy by title.
If the policies do not contain enough information to answer the question, say so.

COMPANY POLICIES:
{policy_database}

EMPLOYEE QUESTION:
{question}

Return your answer in this format:
Relevant policy: [policy title]
Answer: [answer]
"""

max_attempts = 3

start_time = time.time()

for attempt in range(max_attempts):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        print("\n" + response.text)

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
