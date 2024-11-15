
# def ask_symptom(next_symptom):
#     response = f"Do you have {next_symptom}?"
#     return response

# def await_response(user_message, next_symptom, confirmed_symptoms, remaining_symptoms, response_data, positive_response_count):
#     if 'yes' in user_message:
#         positive_response_count += 1
#         confirmed_symptoms.append(next_symptom)
#     elif 'no' in user_message:
#         next_symptom = get_next_symptom(confirmed_symptoms, remaining_symptoms)
#         response_data['bot_message'] = ask_symptom(next_symptom)
#         remaining_symptoms.remove(next_symptom)
#     return confirmed_symptoms, remaining_symptoms, response_data, positive_response_count

# def book_appointment(name, email, phone, doctor, date, time, add_info):
#     doctor = str(doctor).title()
#     name_parts = doctor.split()
#     # Combine "Dr." with the first name
#     first_name = " ".join(name_parts[:2])  # "Dr." + first name
#     last_name = name_parts[2]  # Last name
#     doc_inst = DoctorReg.objects.get(admin__first_name=first_name, admin__last_name=last_name)
#     appointmentnumber = random.randint(100000000, 999999999)
#     # Create a new Appointment instance with the provided data
#     appointmentdetails = Appointment.objects.create(
#         appointmentnumber=appointmentnumber,
#         fullname=name,
#         email=email,
#         mobilenumber=phone,
#         date_of_appointment=date,
#         time_of_appointment=time,
#         doctor_id=doc_inst,
#         additional_msg=add_info,
#     )
#     if appointmentdetails:
#         return 'success', appointmentnumber
#     else:
#         return 'fail', 0
    

# def chat(request):
#     if request.method == "GET":
#         reset_chatbot_session(request)  # Reset session on initial page load
#         return render(request, 'chat.html')
#     elif request.method == "POST":
#         user_message = request.POST.get('message').strip().lower()
#         response_data = {'bot_message': ""}
        
#         if user_message in ["hi", "hello", "hey", "hai"]:
#             response_data['bot_message'] = "Hello! welcome to disease prediction chatbot. Do you experience any symptoms ?"
#             request.session['waiting_for_user_confirmation'] = True
#             return JsonResponse(response_data)
        
#         waiting_for_user_confirmation = request.session.get('waiting_for_user_confirmation', False)
#         waiting_for_appointment_confirmation = request.session.get('waiting_for_appointment_confirmation', False)
#         select_doctor = request.session.get('select_doctor', False)
#         get_user_info = request.session.get('get_user_info', False)
#         get_date_time = request.session.get('get_date_time', False)
#         add_info = request.session.get('add_info', False)
#         # handle_thanks = request.session.get('handle_thanks', False)
        
#         if waiting_for_user_confirmation:
#             if user_message == "yes":
#                 response_data['bot_message'] = "Please enter your symptoms."
#                 request.session['waiting_for_user_confirmation'] = False
#                 return JsonResponse(response_data)
#             elif user_message == "no":
#                 response_data['bot_message'] = "Alright, take care! Let me know if you feel something."
#                 reset_chatbot_session(request)
#                 return JsonResponse(response_data)
        
#         elif "experiencing" in user_message:
#             response_data['bot_message'] = "Please enter your symptoms."
#             return JsonResponse(response_data)
        
#         elif waiting_for_appointment_confirmation:
#             if user_message == "yes":
#                 current_specs = request.session.get('current_specs', False)
#                 if current_specs:
#                     spec_inst = Specialization.objects.get(sname=current_specs)
#                     doctors = DoctorReg.objects.filter(specialization_id=spec_inst.id)
#                     response_data['bot_message'] = "Great! I can assist you with booking an appointment. Please select the doctor you want to meet.<br>"
#                     for doctor in doctors:
#                         response_data['bot_message'] += f"<br>- {doctor.admin.first_name} {doctor.admin.last_name}<br>"
#                     reset_chatbot_session(request)
#                     request.session['select_doctor'] = True
#                     return JsonResponse(response_data)
#             elif user_message == "no":
#                 response_data['bot_message'] = "Alright, feel free to reach out if you change your mind. Take care!"
#                 reset_chatbot_session(request)
#                 return JsonResponse(response_data)
#         elif select_doctor:
#             request.session['doctor_name'] = user_message
#             response_data['bot_message'] = "Please provide your fullname, email id and phone number."
#             request.session['get_user_info'] = True
#             request.session['select_doctor'] = False
#             return JsonResponse(response_data)
#         elif get_user_info:
#             # Regular expression pattern for name, email, and phone number
#             pattern = r"([a-z]+ [a-z]+)\s+([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})\s+(\d{10})"
#             # Matching the pattern (case-insensitive)
#             match = re.match(pattern, user_message, re.IGNORECASE)
#             if match:
#                 name = match.group(1)  # Full name
#                 email = match.group(2)  # Email address
#                 phone = match.group(3)  # Phone number
#             request.session['user_name'] = name
#             request.session['user_email'] = email
#             request.session['user_phone'] = phone
#             response_data['bot_message'] = "Now specify the date and time of your appointment. date(YY-MM-DD) format and time (hh:mm AM/PM) ."
#             request.session['get_date_time'] = True
#             request.session['get_user_info'] = False
#             return JsonResponse(response_data)
#         elif get_date_time:
#             # Regular expression pattern to split date and time
#             pattern = r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2} [APM]{2})"
#             # Matching the pattern
#             match = re.match(pattern, user_message.upper())
#             if match:
#                 date = match.group(1)  # Date part
#                 time = match.group(2)  # Time part
#                 try:
#                     appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
#                     today_date = datetime.now().date()

#                     if appointment_date <= today_date:
#                         # If the appointment date is not in the future, display an error message
#                         response_data['bot_message'] = "Appointment not availabe. Please select a future date."
#                         return JsonResponse(response_data)
#                     else:
#                         request.session['app_date'] = date
#                         request.session['app_time'] = time
#                         response_data['bot_message'] = "If you have any additional information to add in your appointment, please mention. Provide 'nil' if you have nothing to add."
#                         request.session['add_info'] = True
#                 except ValueError:
#                     # Handle invalid date format error
#                     response_data['bot_message'] = "Please provide date in the YY-MM-DD format (eg: 2024-12-20)"
#                     return JsonResponse(response_data)
#             else:
#                 response_data['bot_message'] = "Please provide date and time in the format mentioned."
#                 return JsonResponse(response_data)
#             request.session['get_date_time'] = False
#             return JsonResponse(response_data)
#         elif add_info:
#             request.session['additional_info'] = user_message
#             status, app_id = book_appointment(request.session['user_name'],request.session['user_email'],request.session['user_phone'],request.session['doctor_name'],request.session['app_date'],request.session['app_time'],request.session['additional_info'])
#             if status == 'success':
#                 response_data['bot_message'] = f"Appointment Booked, you can check the status using this appointment number : {app_id}."
#             else:
#                 response_data['bot_message'] = "Appointment cannot be booked now. Some issue occured !"
#             request.session['add_info'] = False
#             reset_chatbot_session(request)
#             return JsonResponse(response_data)
#         elif user_message in ['Ok', 'Thank you', 'Thanks']:
#             response_data['bot_message'] = "Feel free to reach out anytime. Take care!"
#             pass
            
#         else:
#             matched_symptoms = [symptom.strip() for symptom in user_message.split(",") if symptom.strip() in symptom_list or user_message in ['yes', 'no']]
#             if matched_symptoms:
#                 confirmed_symptoms = request.session.get('confirmed_symptoms', [])
#                 remaining_symptoms = request.session.get('remaining_symptoms', [])
#                 positive_response_count = request.session.get('positive_response_count', 0)
#                 confirmed_symptoms.extend(matched_symptoms)
#                 remaining_symptoms = [symptom for symptom in remaining_symptoms if symptom not in confirmed_symptoms]
#                 request.session['confirmed_symptoms'] = confirmed_symptoms
#                 request.session['remaining_symptoms'] = remaining_symptoms
            
#                 predicted_disease, confidence = predict_disease(confirmed_symptoms)
#                 request.session['last_prediction'] = predicted_disease
#                 request.session['prediction_confidence'] = confidence
            
#                 if confidence >= 0.75 or positive_response_count >= 5:
#                     description, precautions = get_disease_info(predicted_disease)
#                     if confidence < 0.75:
#                         disclaimer = f"I am only {confidence * 100:.1f}% confident in this prediction."
#                     else:
#                         disclaimer = ""
                    
#                     # Retrieve specialization
#                     specialization = disease_specialization_df.loc[disease_specialization_df['Disease'] == predicted_disease, 'Specialization'].values
#                     specialization = specialization[0] if len(specialization) > 0 else "unknown"
#                     request.session['current_specs'] = str(specialization)
                    
#                     response_data['bot_message'] = (
#                         f"According to the symptoms you may have {predicted_disease}.<br>"
#                         f"<br>{description}<br><br>Here's some precautions you could take :<br>" +
#                         "<br>".join([f"- {precaution}" for precaution in precautions]) +
#                         (f"<br><br>{disclaimer}" if disclaimer else "")+
#                         f"<br><br>It is recommended that you visit a {specialization} for further assistance."
#                     )
#                     response_data['bot_message'] += "<br><br>Would you like to book an appointment?"
#                     # Set session flag for awaiting appointment response
#                     request.session['waiting_for_appointment_confirmation'] = True
#                     # reset_chatbot_session(request)
#                     return JsonResponse(response_data)
                
#                 next_symptom = get_next_symptom(confirmed_symptoms, remaining_symptoms)
#                 if next_symptom:
#                     response_data['bot_message'] = ask_symptom(next_symptom)
#                     remaining_symptoms.remove(next_symptom)
#                     confirmed_symptoms, remaining_symptoms, response_data, positive_response_count = await_response(user_message, next_symptom, confirmed_symptoms, remaining_symptoms, response_data, positive_response_count)
#                     request.session['positive_response_count'] = positive_response_count
#                     request.session['remaining_symptoms'] = remaining_symptoms
#                     request.session['confirmed_symptoms'] = confirmed_symptoms
                    
#                 else:
#                     response_data['bot_message'] = "I'm out of related symptoms to ask. Let's proceed with the current information."
#             else:
#                 # No matched symptoms; prompt for symptoms
#                 response_data['bot_message'] = "Hello! Do you have any symptoms to mention ?"
#                 request.session['waiting_for_symptom_confirmation'] = True
#         return JsonResponse(response_data)

# Review my code.