from recommendation.src.score import init, run

# Initialize
init()

# Test with sample input
input_data = '{"data": "I want to learn programming basics", "top_k": 5}'
print(run(input_data))