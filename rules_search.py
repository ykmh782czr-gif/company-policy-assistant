import csv

with open("company_policies.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    policies = list(reader)


def search_policies(question):
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


question = input("Ask a policy question: ")
result, score = search_policies(question)

if result:
    print("\nRelevant policy:", result["title"])
    print("Answer:", result["policy_text"])
    print("Match score:", score)
else:
    print("\nNo relevant policy found.")
