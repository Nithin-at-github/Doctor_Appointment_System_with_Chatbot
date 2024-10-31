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

import os
import joblib
import pandas as pd
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Define the absolute path to the directory where your actions.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load the trained model, symptom list, and co-occurrence graph
# with open(os.path.join(current_dir, 'disease_prediction_model.pkl'), 'rb') as file1:
#     model = pickle.load(file1)
# with open(os.path.join(current_dir, 'symptom_list.pkl'), 'rb') as file2:
#     symptom_list = pickle.load(file2)
# with open(os.path.join(current_dir, 'co_occurrence_graph.pkl'), 'rb') as file3:
#     co_occurrence_graph = pickle.load(file3)

model = joblib.load(os.path.join(current_dir, 'disease_prediction_model.pkl'))
symptom_list = joblib.load(os.path.join(current_dir, 'symptom_list.pkl'))
co_occurrence_graph = joblib.load(os.path.join(current_dir, 'co_occurrence_graph.pkl'))

# Load disease description and precaution data
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
    precautions = [precaution_row[f'Precaution_{i+1}'].values[0] 
                   for i in range(4) if f'Precaution_{i+1}' in precaution_row.columns 
                   and pd.notna(precaution_row[f'Precaution_{i+1}'].values[0])]
    return description, precautions

def get_next_symptom(confirmed_symptoms, remaining_symptoms):
    candidates = []
    for symptom in confirmed_symptoms:
        if symptom in co_occurrence_graph:
            for related_symptom, weight in co_occurrence_graph[symptom]:
                if related_symptom in remaining_symptoms:
                    candidates.append((related_symptom, weight))
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    return remaining_symptoms[0] if remaining_symptoms else None

class ActionAskSymptoms(Action):
    def name(self) -> str:
        return "action_ask_symptoms"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        user_symptoms = tracker.get_slot("user_symptoms")
        if not user_symptoms:
            dispatcher.utter_message("Please provide one or more symptoms.")
            return []

        confirmed_symptoms = user_symptoms.split(",")
        remaining_symptoms = [symptom for symptom in symptom_list if symptom not in confirmed_symptoms]

        next_symptom = get_next_symptom(confirmed_symptoms, remaining_symptoms)
        if next_symptom:
            dispatcher.utter_message(f"Do you have {next_symptom}? (yes/no)")
            return [SlotSet("remaining_symptoms", remaining_symptoms), SlotSet("next_symptom", next_symptom)]
        else:
            return []

class ActionPredictDisease(Action):
    def name(self) -> str:
        return "action_predict_disease"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        confirmed_symptoms = tracker.get_slot("confirmed_symptoms")
        if not confirmed_symptoms:
            dispatcher.utter_message("I'm unable to predict the disease without symptoms.")
            return []

        predicted_disease, confidence = predict_disease(confirmed_symptoms)
        if confidence >= 0.75:
            description, precautions = get_disease_info(predicted_disease)
            dispatcher.utter_message(f"The predicted disease is {predicted_disease} with confidence {confidence:.2f}.")
            dispatcher.utter_message(f"Disease Description: {description}")
            dispatcher.utter_message("Precautions to take:")
            for precaution in precautions:
                dispatcher.utter_message(f"- {precaution}")
        else:
            dispatcher.utter_message(f"I'm not confident enough to make a prediction with the provided symptoms.")
        return []
