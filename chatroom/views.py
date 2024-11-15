from django.shortcuts import render
from django.http import JsonResponse
import joblib
import os
import re
import random
import pandas as pd
from dasapp.models import DoctorReg, Specialization, Appointment
from datetime import datetime

# Load model and data files only once (outside view functions for efficiency)
current_dir = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(current_dir, 'disease_prediction_model.pkl'))
symptom_list = joblib.load(os.path.join(current_dir, 'symptom_list.pkl'))
co_occurrence_graph = joblib.load(os.path.join(current_dir, 'co_occurrence_graph1.pkl'))
disease_description_df = pd.read_csv(os.path.join(current_dir, 'disease_description.csv'))
disease_precaution_df = pd.read_csv(os.path.join(current_dir, 'disease_precaution.csv'))
disease_specialization_df = pd.read_csv(os.path.join(current_dir, 'disease_specializations.csv'))

# Initialize state dictionary outside the view
USER_STATES = {}

def reset_user_state(user_id):
    USER_STATES[user_id] = {
        'stage': 'initial_greeting',
        'confirmed_symptoms': [],
        'remaining_symptoms': symptom_list.copy(),
        'positive_response_count': 0,
        'doctor_name': '',
        'user_info': {},
        'appointment_info': {}
    }

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
                   and pd.notna(precaution_row[f'Precaution_{i+1}'].values[0])] if not precaution_row.empty else ["No precautions available."]
    return description, precautions

def await_response(user_message, next_symptom, user_state, response_data):
    print("await_respose loaded")
    if 'yes' in user_message:
        print("yes")
        user_state['positive_response_count'] += 1
        user_state['confirmed_symptoms'].append(next_symptom)
        print(user_state['positive_response_count'])
    elif 'no' in user_message:
        print("no")
        next_symptom = get_next_symptom(user_state['confirmed_symptoms'], user_state['remaining_symptoms'])
        if next_symptom:
            response_data['bot_message'] = ask_symptom(next_symptom)
            user_state['remaining_symptoms'].remove(next_symptom)
    return user_state['confirmed_symptoms'], user_state['remaining_symptoms'], response_data, user_state['positive_response_count']

def ask_symptom(next_symptom):
    return f"Do you have {next_symptom}?"

def book_appointment(user_id):
    user_state = USER_STATES[user_id]
    try:
        doctor_name = user_state['doctor_name']
        name_parts = doctor_name.split()
        first_name = " ".join(name_parts[:2])
        last_name = name_parts[2]
        doc_inst = DoctorReg.objects.get(admin__first_name=first_name, admin__last_name=last_name)
        appointment_number = random.randint(100000000, 999999999)

        appointmentdetails = Appointment.objects.create(
            appointmentnumber=appointment_number,
            fullname=user_state['user_info']['name'],
            email=user_state['user_info']['email'],
            mobilenumber=user_state['user_info']['phone'],
            date_of_appointment=user_state['appointment_info']['date'],
            time_of_appointment=user_state['appointment_info']['time'],
            doctor_id=doc_inst,
            additional_msg=user_state['appointment_info'].get('additional_info', 'nil'),
        )
        return ('success', appointment_number) if appointmentdetails else ('fail', 0)
    except Exception as e:
        return str(e), 0

def chat(request):
    user_id = request.session.session_key
    if not user_id or user_id not in USER_STATES:
        reset_user_state(user_id)
    user_state = USER_STATES[user_id]
    
    if request.method == "GET":
        reset_user_state(user_id)
        return render(request, 'chat.html')
    elif request.method == "POST":
        user_message = request.POST.get('message').strip().lower()
        response_data = {'bot_message': ""}
        
        # Handle greeting
        if user_state['stage'] == 'initial_greeting' and user_message in ["hi", "hello", "hey", "hai"]:
            response_data['bot_message'] = "Hello! Welcome to the disease prediction chatbot. Do you experience any symptoms?"
            user_state['stage'] = 'awaiting_symptom_input'
            return JsonResponse(response_data)

        # Symptom input and disease prediction logic
        if user_state['stage'] == 'awaiting_symptom_input':
            if user_message == "yes":
                response_data['bot_message'] = "Please enter your symptoms."
                user_state['stage'] = 'collecting_symptoms'
                return JsonResponse(response_data)
            elif user_message == "no":
                response_data['bot_message'] = "Alright, take care! Let me know if you feel something."
                reset_user_state(user_id)
                return JsonResponse(response_data)

        elif user_state['stage'] == 'collecting_symptoms':
            # Parsing user symptoms and predicting
            matched_symptoms = [symptom.strip() for symptom in user_message.split(",") if symptom.strip() in symptom_list or user_message in ['yes', 'no']]
            user_state['confirmed_symptoms'].extend(matched_symptoms)
            user_state['remaining_symptoms'] = [s for s in user_state['remaining_symptoms'] if s not in user_state['confirmed_symptoms']]
            
            if matched_symptoms:
                predicted_disease, confidence = predict_disease(user_state['confirmed_symptoms'])
                user_state['last_prediction'] = predicted_disease
                user_state['prediction_confidence'] = confidence
                
                if confidence >= 0.75 or user_state['positive_response_count'] >= 5:
                    description, precautions = get_disease_info(predicted_disease)
                    disclaimer = f"I am only {confidence * 100:.1f}% confident in this prediction." if confidence < 0.75 else ""
                    specialization = disease_specialization_df.loc[disease_specialization_df['Disease'] == predicted_disease, 'Specialization'].values
                    specialization = specialization[0] if len(specialization) > 0 else "unknown"
                    user_state['current_specs'] = specialization
                    
                    response_data['bot_message'] = (
                        f"According to the symptoms, you may have {predicted_disease}.<br>"
                        f"<br>{description}<br><br>Here's some precautions you could take:<br>" +
                        "<br>".join([f"- {precaution}" for precaution in precautions]) +
                        (f"<br><br>{disclaimer}" if disclaimer else "")+
                        f"<br><br>It is recommended that you visit a {specialization} for further assistance.<br><br>Would you like to book an appointment?"
                    )
                    user_state['stage'] = 'awaiting_appointment_confirmation'
                    return JsonResponse(response_data)

                next_symptom = get_next_symptom(user_state['confirmed_symptoms'], user_state['remaining_symptoms'])
                if next_symptom:
                    response_data['bot_message'] = ask_symptom(next_symptom)
                    user_state['remaining_symptoms'].remove(next_symptom)
                    user_state['confirmed_symptoms'], user_state['remaining_symptoms'], response_data, user_state['positive_response_count'] = await_response(user_message, next_symptom, user_state, response_data)
                else:
                    response_data['bot_message'] = "I'm out of related symptoms to ask. Let's proceed with the current information."

            return JsonResponse(response_data)

        elif user_state['stage'] == 'awaiting_appointment_confirmation':
            if user_message == "yes":
                spec_inst = Specialization.objects.get(sname=user_state['current_specs'])
                doctors = DoctorReg.objects.filter(specialization_id=spec_inst.id)
                response_data['bot_message'] = "Please select a doctor:<br>" + "<br>".join([f"- {doc.admin.first_name} {doc.admin.last_name}" for doc in doctors])
                user_state['stage'] = 'selecting_doctor'
                return JsonResponse(response_data)
            elif user_message == "no":
                response_data['bot_message'] = "Alright, take care! Feel free to reach out if you change your mind."
                reset_user_state(user_id)
                return JsonResponse(response_data)

        elif user_state['stage'] == 'selecting_doctor':
            user_state['doctor_name'] = user_message.title()
            response_data['bot_message'] = "Please provide your full name, email, and phone number."
            user_state['stage'] = 'awaiting_user_info'
            return JsonResponse(response_data)

        elif user_state['stage'] == 'awaiting_user_info':
            match = re.match(r"([a-z]+ [a-z]+)\s+([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})\s+(\d{10})", user_message, re.IGNORECASE)
            if match:
                user_state['user_info'] = {'name': match.group(1), 'email': match.group(2), 'phone': match.group(3)}
                response_data['bot_message'] = "Specify the appointment date (YY-MM-DD) and time (hh:mm AM/PM)."
                user_state['stage'] = 'awaiting_date_time'
            else:
                response_data['bot_message'] = "Please provide valid name, email, and phone number."
            return JsonResponse(response_data)

        elif user_state['stage'] == 'awaiting_date_time':
            match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2} [APM]{2})", user_message.upper())
            if match:
                date = match.group(1)
                time = match.group(2)
                if datetime.strptime(date, "%Y-%m-%d").date() <= datetime.now().date():
                    response_data['bot_message'] = "Select a future date for the appointment."
                else:
                    user_state['appointment_info'] = {'date': date, 'time': time}
                    response_data['bot_message'] = "Provide any additional info for the appointment, or 'nil' if none."
                    user_state['stage'] = 'awaiting_additional_info'
            else:
                response_data['bot_message'] = "Provide date and time in the specified format."
            return JsonResponse(response_data)

        elif user_state['stage'] == 'awaiting_additional_info':
            user_state['appointment_info']['additional_info'] = user_message
            status, app_id = book_appointment(user_id)
            response_data['bot_message'] = (
                f"Appointment booked. You can use this number : {app_id} to check the appointment status." if status == 'success' else
                "Unable to book appointment. Please try again."
            )
            reset_user_state(user_id)
            return JsonResponse(response_data)

        # Default response
        response_data['bot_message'] = "Hello! Do you have any symptoms to mention?"
        return JsonResponse(response_data)