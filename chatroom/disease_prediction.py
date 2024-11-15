import numpy as np

class DiseasePredictor:
    def __init__(self, model, symptom_graph):
        self.model = model
        self.symptom_graph = symptom_graph
        self.confirmed_symptoms = set()
        self.predicted_disease = None
        self.prediction_confidence = 0.0

    def update_confirmed_symptoms(self, symptoms):
        self.confirmed_symptoms.update(symptoms)

    def suggest_next_symptom(self):
        for symptom in self.confirmed_symptoms:
            related_symptoms = self.symptom_graph.get(symptom, [])
            for related_symptom in related_symptoms:
                if related_symptom not in self.confirmed_symptoms:
                    return related_symptom
        return None

    def predict_disease(self):
        if not self.confirmed_symptoms:
            return None, 0.0

        symptom_vector = self._symptoms_to_vector(self.confirmed_symptoms)
        prediction = self.model.predict([symptom_vector])[0]
        confidence = np.max(self.model.predict_proba([symptom_vector])[0])
        
        self.predicted_disease = prediction
        self.prediction_confidence = confidence
        
        return prediction, confidence

    def _symptoms_to_vector(self, symptoms):
        symptom_list = sorted(self.symptom_graph.keys())
        return [1 if symptom in symptoms else 0 for symptom in symptom_list]

    def get_disease_info(self):
        # Mock disease information retrieval
        description = f"{self.predicted_disease} is a condition..."
        precautions = ["Stay hydrated", "Rest", "Consult a healthcare provider"]
        return description, precautions
