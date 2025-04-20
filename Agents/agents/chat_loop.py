# chat_loop.py

from agents.chat_agent import chat_agent

def start_chat_agent(context):
    print("\n💬 You can now chat with your study assistant! Type 'exit' to quit.\n")

    chat_history = [
        f"You are a helpful assistant helping a student with study planning.",
        f"Here is the user's context:\n{context}"
    ]

    while True:
        user_input = input("🧑 You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        chat_history.append(f"User: {user_input}")

        full_prompt = "\n".join(chat_history) + "\nAssistant:"
        response = chat_agent.llm.predict(full_prompt)

        print(f"🤖 Assistant: {response}\n")
        chat_history.append(f"Assistant: {response}")
