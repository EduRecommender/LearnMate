from app.recommendations.CourseRecommender import CourseRecommender2 as Model

def test_load_data():
    recommender = Model()
    recommender.load_data()
    assert not recommender.data.empty, "Data should load successfully"

def test_predict():
    recommender = Model()
    recommender.load_data()
    recommender.train()
    predictions = recommender.predict("I want to learn programming basics", top_k=5)
    assert len(predictions) == 5, "Should return 5 recommendations"

if __name__ == "__main__":
    test_load_data()
    test_predict()
