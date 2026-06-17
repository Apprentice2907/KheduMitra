import pytest
from app.services.intent_classifier import IntentClassifier

def test_intent_classifier_fallback():
    # If model is not loaded, it should return Unknown
    classifier = IntentClassifier()
    classifier.model = None
    assert classifier.predict("Some query") == "Unknown"
