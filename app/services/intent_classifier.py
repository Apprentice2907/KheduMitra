import os
import pickle
import logging

logger = logging.getLogger(__name__)

class IntentClassifier:
    def __init__(self):
        self.model = None
        self._load_model()
        
    def _load_model(self):
        intent_model_path = os.path.join("models", "intent_classifier.pkl")
        if os.path.exists(intent_model_path):
            try:
                with open(intent_model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("Intent classifier loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load intent classifier: {e}")
                
    def predict(self, text: str) -> str:
        if self.model:
            try:
                return self.model.predict([text])[0]
            except Exception as e:
                logger.debug(f"Intent prediction failed: {e}")
        return "Unknown"

intent_classifier_service = IntentClassifier()
