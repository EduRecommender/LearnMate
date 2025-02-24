import openai

client = openai.OpenAI(api_key="KEY HERE")

def chatbot(prompt):
    response = client.chat.completions.create(
        model = "gpt-4o",
        messages = [
            {"role": "system", "content": "You are an AI tutor called LearnMate, you are specialized in Math, Business, Computer Science and Design. Provide clear, accurate, and educational responses."},
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