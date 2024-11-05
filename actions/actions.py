# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
import pandas as pd
import joblib
import os

# Define the absolute path to the directory where your actions.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load the model and data files
model = joblib.load(os.path.join(current_dir, 'disease_prediction_model.pkl'))
symptom_list = joblib.load(os.path.join(current_dir, 'symptom_list.pkl'))
co_occurrence_graph = joblib.load(os.path.join(current_dir, 'co_occurrence_graph.pkl'))
disease_description_df = pd.read_csv(os.path.join(current_dir, 'disease_description.csv'))
disease_precaution_df = pd.read_csv(os.path.join(current_dir, 'disease_precaution.csv'))

def predict_disease(symptoms):
    symptom_vector = [1 if symptom in symptoms else 0 for symptom in symptom_list]
    input_df = pd.DataFrame([symptom_vector], columns=symptom_list)
    predicted_disease = model.predict(input_df)[0]
    probabilities = model.predict_proba(input_df)
    confidence = max(probabilities[0])
    return predicted_disease, confidence

def get_disease_info(disease):
    description_row = disease_description_df[disease_description_df['Disease'].str.lower() == disease.lower()]
    description = description_row['Description'].values[0] if not description_row.empty else "No description available."

    precaution_row = disease_precaution_df[disease_precaution_df['Disease'].str.lower() == disease.lower()]
    precautions = [precaution_row[f'Precaution_{i+1}'].values[0] for i in range(4) 
                   if f'Precaution_{i+1}' in precaution_row.columns and pd.notna(precaution_row[f'Precaution_{i+1}'].values[0])]
    return description, precautions if precautions else ["No precautions available."]

class ActionPredictDisease(Action):
    def name(self) -> str:
        return "action_predict_disease"
    
    def run(self, dispatcher, tracker, domain):
        confirmed_symptoms = tracker.get_slot("confirmed_symptoms") or []
        
        # Create a feature vector based on the confirmed symptoms
        symptom_vector = [1 if symptom in confirmed_symptoms else 0 for symptom in symptom_list]
        input_df = pd.DataFrame([symptom_vector], columns=symptom_list)
        
        # Get disease prediction and confidence
        disease, confidence = predict_disease(confirmed_symptoms)
        
        # Always set the disease_prediction and prediction_confidence slots
        events = [
            SlotSet("disease_prediction", disease),
            SlotSet("prediction_confidence", confidence)
        ]
        
        # Only display message if confidence is above the threshold
        if confidence >= 0.75:
            description, precautions = get_disease_info(disease)
            dispatcher.utter_message(text=f"The predicted disease is {disease} with confidence {confidence:.2f}.")
            dispatcher.utter_message(text=f"Disease Description: {description}")
            dispatcher.utter_message(text="Precautions to take:")
            for precaution in precautions:
                dispatcher.utter_message(text=f"- {precaution}")
        
        return events

class ActionSuggestNextSymptom(Action):
    def name(self):
        return "action_suggest_next_symptom"

    def run(self, dispatcher, tracker, domain):
        confirmed_symptoms = tracker.get_slot("confirmed_symptoms") or []
        remaining_symptoms = tracker.get_slot("remaining_symptoms") or [
            symptom for symptom in symptom_list if symptom not in confirmed_symptoms
        ]
        
        # Identify next symptom based on co-occurrence graph
        candidates = [
            (related_symptom, weight) for symptom in confirmed_symptoms 
            if symptom in co_occurrence_graph for related_symptom, weight in co_occurrence_graph[symptom]
            if related_symptom in remaining_symptoms
        ]
        
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            next_symptom = candidates[0][0]
            remaining_symptoms.remove(next_symptom)
            dispatcher.utter_message(template="utter_ask_next_symptom", next_symptom=next_symptom)
            
            # Always update remaining symptoms slot
            return [SlotSet("remaining_symptoms", remaining_symptoms)]
        
        # Fallback in case no candidates are found
        dispatcher.utter_message(text="No additional relevant symptoms to ask about.")
        return [SlotSet("remaining_symptoms", remaining_symptoms)]
