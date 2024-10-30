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

import random
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import pickle

# Load your disease prediction model and symptom list
with open('disease_prediction_model.pkl', 'rb') as file:
    model = pickle.load(file)

with open('symptom_list.pkl', 'rb') as symlist:
    symptom_list = pickle.load(symlist)

with open('co_occurrence_graph.pkl', 'rb') as coocgraph:
    co_occurrence_graph = pickle.load(coocgraph)

class ActionPredictDisease(Action):
    def name(self) -> Text:
        return "action_predict_disease"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        confirmed_symptoms = tracker.get_slot('confirmed_symptoms')

        if confirmed_symptoms:
            predicted_disease = self.predict_disease(confirmed_symptoms)
            dispatcher.utter_message(text=f"Based on your symptoms, the predicted disease is {predicted_disease}")
        else:
            dispatcher.utter_message(text="I need more symptoms to make a prediction.")

        return []

    def predict_disease(self, symptoms: List[Text]) -> Text:
        # Create a feature vector for the prediction
        symptom_vector = [1 if symptom in symptoms else 0 for symptom in symptom_list]
        prediction = model.predict([symptom_vector])
        return prediction[0]


class ActionNextSymptom(Action):
    def name(self) -> Text:
        return "action_next_symptom"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        confirmed_symptoms = tracker.get_slot('confirmed_symptoms') or []
        remaining_symptoms = [s for s in symptom_list if s not in confirmed_symptoms]

        # Get the next symptom based on the co-occurrence graph
        next_symptom = self.get_next_symptom(confirmed_symptoms, remaining_symptoms)

        if next_symptom:
            dispatcher.utter_message(text=f"Are you also experiencing {next_symptom}?")
        else:
            dispatcher.utter_message(text="No additional relevant symptoms to ask about.")

        return []

    def get_next_symptom(self, confirmed_symptoms: List[Text], remaining_symptoms: List[Text]) -> Text:
        candidates = []
        for symptom in confirmed_symptoms:
            if symptom in co_occurrence_graph:
                for related_symptom, weight in co_occurrence_graph[symptom]:
                    if related_symptom in remaining_symptoms:
                        candidates.append((related_symptom, weight))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # Fallback: return a random symptom
        return random.choice(remaining_symptoms) if remaining_symptoms else None