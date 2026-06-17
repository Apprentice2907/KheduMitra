import os
import pickle
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline

# 4 buckets: crop_disease, market_price, govt_scheme, weather
def generate_training_data():
    examples = {
        "crop_disease": [
            "meri fasal mein disease hai",
            "cotton leaves are curling",
            "kapaas ke patte mod rahe hain",
            "wheat has yellow spots",
            "gehu me pila ratua lag gaya hai",
            "what to spray for whitefly",
            "safed makhi ki dawai batao",
            "crop is turning yellow",
            "fasal sukh rahi hai",
            "patton par dhabbe hain",
            "leaves have brown spots",
            "disease in tomato plant",
            "tamatar me keeda lag gaya",
            "pesticide for fungus",
            "fungicide for yellow rust"
        ],
        "market_price": [
            "mandi bhav kya hai",
            "what is the price of cotton",
            "aaj ka kapaas ka rate",
            "wheat price in punjab",
            "gehu ka kya bhav chal raha hai",
            "how much is soybean selling for",
            "soybean ka mandi rate",
            "onion price nasik",
            "pyaz ka bhav batao",
            "market price for tomato",
            "tamatar mandi bhav",
            "rate of mustard today",
            "sarson ka price kya hai",
            "is it a good time to sell wheat",
            "bhav kab badhega"
        ],
        "govt_scheme": [
            "kya PM-KISAN ka paisa aaya",
            "pm kisan installment status",
            "mera registration number hai",
            "how to apply for pmfby",
            "fasal bima yojana kya hai",
            "crop insurance details",
            "subsidy for tractor",
            "tractor ki subsidy kaise milegi",
            "kisan credit card apply",
            "kcc loan kaise le",
            "government schemes for farmers",
            "sarkari yojana batao",
            "when will 14th installment come",
            "mera kisan samman nidhi ka paisa nahi aaya",
            "eligibility for pm kisan"
        ],
        "weather": [
            "aaj ka mausam kaisa hai",
            "weather forecast for tomorrow",
            "kal barish hogi kya",
            "will it rain today",
            "pune district weather",
            "pune ka mausam batao",
            "temperature kya hai",
            "kitni dhoop niklegi",
            "is there a storm warning",
            "toofan aane wala hai kya",
            "humidity in nashik",
            "nashik me barish kab hogi",
            "when will monsoon arrive",
            "monsoon kab aayega",
            "weather updates for next 3 days"
        ]
    }

    # Generate 500+ examples by augmenting
    X = []
    y = []
    
    fillers_prefix = ["mujhe batao ", "please tell me ", "kya aap jante hain ", "sir ", "hello ", ""]
    fillers_suffix = [" please", " ji", " yaar", " abhi", ""]

    for intent, sentences in examples.items():
        # Duplicate and augment
        for _ in range(40): # 40 * 15 = 600 total per class roughly, total 2400
            for sentence in sentences:
                prefix = random.choice(fillers_prefix)
                suffix = random.choice(fillers_suffix)
                augmented = f"{prefix}{sentence}{suffix}".strip().lower()
                X.append(augmented)
                y.append(intent)

    return X, y

def main():
    print("Generating synthetic training data...")
    X, y = generate_training_data()
    print(f"Total examples generated: {len(X)}")

    print("Training intent classifier (Tfidf + LinearSVC)...")
    pipeline = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), LinearSVC())
    pipeline.fit(X, y)

    # Evaluate on training set
    accuracy = pipeline.score(X, y)
    print(f"Training accuracy: {accuracy * 100:.2f}%")

    os.makedirs("models", exist_ok=True)
    model_path = "models/intent_classifier.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    main()
