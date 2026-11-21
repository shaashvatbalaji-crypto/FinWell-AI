import json
from services.ai_query_orchestrator import answer_financial_question

user_id = int(input("Enter your FinWell user ID: "))

print("\n=== FINWELL AI TERMINAL ===")
print("Type exit to quit.")

while True:
    question = input("\nYou: ").strip()

    if question.lower() in ("exit", "quit"):
        break

    if not question:
        continue

    try:
        result = answer_financial_question(user_id, question)

        print("\nQWEN:")
        print(result.get("answer"))

        print("\nSOURCES:", result.get("sources"))
        print("\nRETRIEVAL STATUS:")
        print(json.dumps(result.get("retrieval_status"), indent=2, default=str))

    except Exception as error:
        print("\nERROR:", repr(error))
