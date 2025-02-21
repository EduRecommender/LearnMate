import openai

client = openai.OpenAI(api_key="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")

def chatbot(prompt):
    response = client.chat.completions.create(
        model = "gpt-4o",
        messages = [
            {"role": "system", "content": "You are an AI tutor called LearnMate, you are specialized in Math, Science, Language and History. Provide clear, accurate, and educational responses."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    print("Hello I am LearnMate AI, how can I assist you today?")

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            break

        response = chatbot(user_input)
        print("LearnMate:", response)