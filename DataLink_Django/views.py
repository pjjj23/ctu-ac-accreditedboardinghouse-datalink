from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import HttpRequest
from django.contrib import messages
import hashlib
from .firebase import auth_instance,db   
import time, threading
from django.utils import timezone
import random
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .firebase import storage 
import uuid, math
import json
from django.views.decorators.csrf import csrf_exempt
import os, re
from uuid import uuid4
import requests
from datetime import datetime, timedelta
import logging
from django.urls import reverse
from django.core.mail import EmailMessage
from django.utils.html import strip_tags
from django.views import View
from collections import Counter
import pytz
import csv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create your views here.

def log_ip_and_url(ip_address, current_url, url_description, user_email=None, user_status=None, user_role=None):
    """
    Logs the user's IP address, the URL they visited, and additional metadata.
    Adds the logged-in user's email as "identity", "active_status", and "role" if provided.
    Also calculates the active status based on last visited time and updates accordingly.
    """

    valid_ip_address = ip_address.replace('.', '_')  # Firebase-safe key

    if valid_ip_address:
        # Retrieve existing data for the IP address
        existing_data_response = db.child("fetchedusersIPaddress").child(valid_ip_address).get()

        # Check if data exists in the response
        existing_data = existing_data_response.val() if existing_data_response.val() else {}

        # Initialize if no data exists
        if not existing_data:
            existing_data = {
                "ip": ip_address,
                "urls_visited": [],
                "last_visited": str(datetime.now(pytz.timezone('Asia/Manila'))),  # Set the timezone correctly
                "active_status": "Inactive",  # Default to Inactive
            }

        # Fetch existing URLs and append the new description if the URL has changed
        urls_visited = existing_data.get("urls_visited", [])
        current_time = datetime.now(pytz.timezone('Asia/Manila'))

        # Update `last_visited` and `active_status` if a new URL is visited
        if not urls_visited or urls_visited[-1] != url_description:
            urls_visited.append(url_description)  # Save descriptive URL instead of raw path
            urls_visited = urls_visited[-5:]  # Retain only the last 5 URLs
            existing_data["urls_visited"] = urls_visited
            existing_data["last_visited"] = str(current_time)  # Update last visited timestamp
            existing_data["active_status"] = "Active"  # Mark as active on new activity

        # Function to check for inactivity and update status
        def check_inactivity():
            try:
                last_visited_time = datetime.fromisoformat(existing_data["last_visited"])
            except ValueError:
                print("Error parsing last_visited time. Resetting to current time.")
                last_visited_time = current_time  # Use current time as fallback

            time_difference = datetime.now(pytz.timezone('Asia/Manila')) - last_visited_time

            # Debugging print to check time difference
            print(f"Time difference: {time_difference}")

            # If no new activity, update status to "Inactive"
            if time_difference > timedelta(seconds=2):
                existing_data["active_status"] = "Inactive"
                db.child("fetchedusersIPaddress").child(valid_ip_address).set(existing_data)
                print(f"Updated active_status to 'Inactive' for IP {valid_ip_address}")
            else:
                print(f"User is still active for IP {valid_ip_address}")

        # Update additional fields if provided (identity and role)
        if user_email:
            existing_data["identity"] = user_email
        if user_role:
            existing_data["role"] = user_role

        # Save data to Firebase
        db.child("fetchedusersIPaddress").child(valid_ip_address).set(existing_data)
        print(f"Saved data for IP {valid_ip_address}: {existing_data}")

        # Start a timer to check inactivity after 2 seconds
        threading.Timer(3, check_inactivity).start()

        return existing_data["active_status"]







def home(request: HttpRequest):
    # Get the user's IP address
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')

    # Get the current URL being accessed
    current_url = request.path

    # Log IP and URL with a descriptive value
    log_ip_and_url(ip_address, current_url, "home/")  # Provide a description for the home page

    usersfetchedIPcontext = {
        'ip_address': ip_address,
        'urls_visited': []  # Can keep it empty or display visited URLs if needed
    }
    return render(request, 'index.html', usersfetchedIPcontext)


def custom_404(request, exception):
    return render(request, '404.html', status=404)
def aboutus(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "/aboutus")
    return render(request, 'aboutus.html')


# Users complain
def owner_report_problem(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "owner/owner_login/owner_report_problem")
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Format email key for Firebase query
        email_key = email.replace('.', '_').replace('@', '_at_')

        try:
            # Check if the email exists in the 'owners' table in Firebase
            owner_data = db.child("owners").child(email_key).get()

            if owner_data.val():
                # If email exists, proceed with saving the report
                date_of_report = datetime.now().strftime("%B %d, %Y %I:%M %p")

                report_data = {
                    "name": name,
                    "email": email,
                    "message": message,
                    "date_of_report": date_of_report,
                    "status": "unfixed"
                }

                # Save the report data under the email_key in messages
                db.child("usersReport").child("owners").child(email_key).child("messages").push(report_data)
                messages.success(request, 'Your report has been sent. Please wait for the response.')
            else:
                # If email doesn't exist, show error
                messages.error(request, 'Only the owners with account registered can report.')

        except Exception as e:
            error_message = str(e)
            print(f"Exception occurred: {error_message}")  # Debugging
            messages.error(request, f'Error processing your request: {error_message}')

        return redirect('owner_report_problem')

    return render(request, 'owner_report.html')


def student_report_problem(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/student_login/student_report_problem")
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Format email key for Firebase query
        email_key = email.replace('.', '_').replace('@', '_at_')

        try:
            # Check if the email exists in the 'owners' table in Firebase
            student_data = db.child("students").child(email_key).get()

            if student_data.val():
                # If email exists, proceed with saving the report
                date_of_report = datetime.now().strftime("%B %d, %Y %I:%M %p")

                report_data = {
                    "name": name,
                    "email": email,
                    "message": message,
                    "date_of_report": date_of_report,
                    "status": "unfixed"
                }

                # Save the report data under the email_key in messages
                db.child("usersReport").child("students").child(email_key).child("messages").push(report_data)
                messages.success(request, 'Your report has been sent. Please wait for the response.')
            else:
                # If email doesn't exist, show error
                messages.error(request, 'Only the students with account registered can report.')

        except Exception as e:
            error_message = str(e)
            print(f"Exception occurred: {error_message}")  # Debugging
            messages.error(request, f'Error processing your request: {error_message}')

        return redirect('student_report_problem')

    return render(request, 'student_report.html')


def student_report(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/saofeedback/student_report")
    if request.method == "POST":
        # Get the report key and email from the POST request
        report_key = request.POST.get('report_key')
        email = request.POST.get('email')

        # Format the email key for Firebase query
        email_key = email.replace('.', '_').replace('@', '_at_')

        print(f"Report Key: {report_key}")  # Debugging
        print(f"Email Key: {email_key}")  # Debugging

        if report_key and email_key:
            # Update the status of the report to 'fixed' in Firebase
            try:
                db.child("usersReport").child("students").child(email_key).child("messages").child(report_key).update({"status": "fixed"})
                print("Status updated to 'fixed'")  # Debugging
            except Exception as e:
                print(f"Error updating status: {e}")  # Debugging
            return redirect('student_report')

    # Fetch all student reports from Firebase
    student_reports = db.child("usersReport").child("students").get().val()

    # Prepare a list to hold all feedback reports
    feedback_list = []

    # Check if the data exists
    if student_reports:
        # Iterate through each student entry
        for email_key, student_data in student_reports.items():
            # Retrieve messages for each student
            reports = student_data.get("messages", {})
            
            # If there are any reports/messages, add them to the feedback list
            for key, report_data in reports.items():
                feedback_list.append({
                    'key': key,  # Add the key for identifying the report
                    'name': report_data.get('name', 'N/A'),
                    'email': report_data.get('email', 'N/A'),
                    'date_of_report': report_data.get('date_of_report', 'N/A'),
                    'message': report_data.get('message', 'No message available'),
                    'status': report_data.get('status', 'unfixed')  # Include status in the feedback data
                })
    else:
        print("No student reports found in Firebase.")

    # Prepare the context with all feedback data
    context = {
        'feedback_data': feedback_list
    }

    # Render the SAO-studentreport.html template with the feedback data
    return render(request, 'SAO-studentreport.html', context)

def owner_report(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/saofeedback/owner_report")
    if request.method == "POST":
        # Get the report key and email from the POST request
        report_key = request.POST.get('report_key')
        email = request.POST.get('email')

        # Format the email key for Firebase query
        email_key = email.replace('.', '_').replace('@', '_at_')

        print(f"Report Key: {report_key}")  # Debugging
        print(f"Email Key: {email_key}")  # Debugging

        if report_key and email_key:
            # Update the status of the report to 'fixed' in Firebase
            try:
                db.child("usersReport").child("owners").child(email_key).child("messages").child(report_key).update({"status": "fixed"})
                print("Status updated to 'fixed'")  # Debugging
            except Exception as e:
                print(f"Error updating status: {e}")  # Debugging
            return redirect('owner_report')

    # Fetch all owner reports from Firebase
    student_reports = db.child("usersReport").child("owners").get().val()

    # Prepare a list to hold all feedback reports
    feedback_list = []

    # Check if the data exists
    if student_reports:
        # Iterate through each student entry
        for email_key, student_data in student_reports.items():
            # Retrieve messages for each student
            reports = student_data.get("messages", {})
            
            # If there are any reports/messages, add them to the feedback list
            for key, report_data in reports.items():
                feedback_list.append({
                    'key': key,  # Add the key for identifying the report
                    'name': report_data.get('name', 'N/A'),
                    'email': report_data.get('email', 'N/A'),
                    'date_of_report': report_data.get('date_of_report', 'N/A'),
                    'message': report_data.get('message', 'No message available'),
                    'status': report_data.get('status', 'unfixed')  # Include status in the feedback data
                })
    else:
        print("No student reports found in Firebase.")

    # Prepare the context with all feedback data
    context = {
        'feedback_data': feedback_list
    }

    # Render the SAO-studentreport.html template with the feedback data
    return render(request, 'SAO-ownerreport.html', context)






def rejectstudents(request):
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')

    # Specific active page for homepage
    context['active_page'] = 'undo'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 

    if request.method == 'POST':
        # Determine the action based on the button clicked
        action = request.POST.get('action')  # e.g., "restore" or "update"
        email = request.POST.get('email')

        if not email:
            messages.error(request, "Email not provided.")
            return redirect("rejectstudents")
        
        # Convert the email to the key format used in Firebase
        email_key = email.replace('.', '_').replace('@', '_at_')

        try:
            if action == 'restore':
                # Restore account to "pending" status
                db.child("students").child(email_key).update({"accountStatus": "pending"})
                messages.success(request, "Student account restored successfully. It will be found in pending request.")

            elif action == 'update':
                # Get the updated student details from the form
                username = request.POST.get('username')
                student_id = request.POST.get('student_id')
                course = request.POST.get('course')
                gender = request.POST.get('gender')

                # Prepare data to update, omitting empty fields
                update_data = {
                    "username": username,
                    "student_id": student_id,
                    "course": course,
                    "gender": gender,
                }
                update_data = {k: v for k, v in update_data.items() if v}

                # Update student information in Firebase
                db.child("students").child(email_key).update(update_data)
                messages.success(request, "Student information updated successfully.")
                
        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")

    # Retrieve all students and add to context (existing logic)
    try:
        students_data = db.child("students").get().val()

        if isinstance(students_data, dict):
            rejected_students = []
            for email_key, student_info in students_data.items():
                if isinstance(student_info, dict) and student_info.get("accountStatus") == "rejected":
                    rejected_students.append({
                        "email": email_key.replace('_at_', '@').replace('_', '.'),
                        "username": student_info.get("username", ""),
                        "course": student_info.get("course", ""),
                        "gender": student_info.get("gender", ""),
                        "profile_picture": student_info.get("profile_picture", ""),
                        "accountStatus": student_info.get("accountStatus", ""),
                        "student_id": student_info.get("student_id", ""),
                        "disableReason": student_info.get("disableReason", "")
                    })
            context['rejected_students'] = rejected_students
        else:
            context['rejected_students'] = []

    except Exception as e:
        messages.error(request, f"Error fetching rejected students: {str(e)}")
        context['rejected_students'] = []

    return render(request, 'sao-RejectedStudents.html', context)


def rejectowners(request):
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')

    # Specific active page for homepage
    context['active_page'] = 'undo'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 

    if request.method == 'POST':
        action = request.POST.get('action')
        email = request.POST.get('email')

        if not email:
            messages.error(request, "Email not provided.")
            return redirect("sao-RejectedOwners")

        # Convert the email to the key format used in Firebase (replace '.' with '_')
        email_key = email.replace('.', '_').replace('@', '_at_')

        if action == 'restore':
            # Restore the owner to pending status in Firebase
            try:
                db.child("owners").child(email_key).update({"accountStatus": "pending"})
                messages.success(request, "Owner account restored successfully. It will be found in pending requests.")
            except Exception as e:
                messages.error(request, f"Error restoring account: {str(e)}")

        elif action == 'update':
            # Get the updated owner details from the form
            firstname = request.POST.get('firstname')
            middlename = request.POST.get('middlename')
            lastname = request.POST.get('lastname')
            gender = request.POST.get('gender')
            address = request.POST.get('address') 
            
            # Prepare data to update, omitting empty fields
            update_data = {
                "firstname": firstname,
                "middlename": middlename,
                "lastname": lastname,
                "gender": gender,
                "address": address 
            }

            # Only update the fields that have values
            update_data = {k: v for k, v in update_data.items() if v or v == ""}

            # Update owner information in Firebase
            try:
                db.child("owners").child(email_key).update(update_data)
                messages.success(request, "Owner information updated successfully.")
            except Exception as e:
                messages.error(request, f"Error updating owner information: {str(e)}")

    # Retrieve all owners and add to context (existing logic for fetching)
    try:
        owners_data = db.child("owners").get().val()

        if isinstance(owners_data, dict):
            rejected_owners = []
            for email_key, owner_info in owners_data.items():
                if isinstance(owner_info, dict) and owner_info.get("accountStatus") == "rejected":
                    # Retrieve additional data for each owner
                    owner_details = {
                        "email": email_key.replace('_at_', '@').replace('_', '.'),  # Convert back to email format
                        "firstname": owner_info.get("firstname", ""),
                        "middlename": owner_info.get("middlename", ""),
                        "lastname": owner_info.get("lastname", ""),
                        "gender": owner_info.get("gender", ""),
                        "address": owner_info.get("address", ""),
                        "rejectionReason": owner_info.get("rejectionReason", ""),
                        "accountStatus": owner_info.get("accountStatus", ""),
                        "profile_picture": owner_info.get("profile_picture", ""),
                    }

                    # Fetch additional data for boarding house details and amenities/documents
                    try:
                        boardinghouse_data = db.child("ownersBoardingHouse").child(email_key).get().val()
                        if boardinghouse_data:
                            owner_details.update({
                                "boardinghouseName": boardinghouse_data.get("boardinghouseName", ""),
                                "documents": boardinghouse_data.get("documents", []),
                                "amenities": boardinghouse_data.get("amenities", []),
                                "securityFeatures_cctv": boardinghouse_data.get("securityFeatures_cctv", ""),
                                "securityFeatures_curfew": boardinghouse_data.get("securityFeatures_curfew", ""),
                                "securityFeatures_keys": boardinghouse_data.get("securityFeatures_keys", "")
                            })
                    except Exception as e:
                        print(f"Error fetching boarding house data: {str(e)}")

                    rejected_owners.append(owner_details)

            context['rejected_owners'] = rejected_owners
        else:
            context['rejected_owners'] = []

    except Exception as e:
        messages.error(request, f"Error fetching rejected owners: {str(e)}")
        context['rejected_owners'] = []

    return render(request, 'sao-RejectedOwners.html', context)


def disablestudents(request):
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Handle form submission to restore student account
    if request.method == "POST" and request.POST.get('action') == 'restore':
        student_email = request.POST.get('student_email')
        email_key = student_email.replace('.', '_').replace('@', '_at_')
        
        # Fetch student data and update accountStatus
        student_ref = db.child("students").child(email_key)
        student_ref.update({"accountStatus": "approved"})
        
        messages.success(request, f'Account of {student_email} has been enabled and approved.')
        return redirect('disablestudents')  # Redirect to the same page to see updated data

    # Fetch all student data from Firebase
    students_data = db.child("students").get().val()
    
    # Filter students with 'accountStatus' set to 'disabled' and extract specified fields
    disabled_students = []
    if students_data:
        for email_key, student_info in students_data.items():
            if student_info.get('accountStatus') == 'disabled':
                # Build the student dictionary with only the needed fields
                student = {
                    "email": email_key.replace('_at_', '@').replace('_', '.'),
                    "username": student_info.get("username", ""),
                    "course": student_info.get("course", ""),
                    "gender": student_info.get("gender", ""),
                    "profile_picture": student_info.get("profile_picture", ""),
                    "accountStatus": student_info.get("accountStatus", ""),
                    "student_id": student_info.get("student_id", "")
                }
                disabled_students.append(student)
    
    # Add the list of disabled students to context
    context['disabled_students'] = disabled_students
    context['active_page'] = 'undo'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 
    # Pass the context to the template
    return render(request, 'sao-DisabledStudents.html', context)


def disableowners(request):
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Handle form submission to restore owner account
    if request.method == "POST" and request.POST.get('action') == 'restore':
        owner_email = request.POST.get('email')
        email_key = owner_email.replace('.', '_').replace('@', '_at_')
        
        # Fetch owner data and update accountStatus
        owner_ref = db.child("owners").child(email_key)
        owner_ref.update({"accountStatus": "approved"})
        
        # Fetch the corresponding boarding house data and update boardinghouseStatus
        boardinghouse_ref = db.child("ownersBoardingHouse").child(email_key)
        boardinghouse_ref.update({"boardinghouseStatus": "approved"})
        
        messages.success(request, f'Account of {owner_email} has been enabled and approved.')
        return redirect('disableowners')  # Redirect to the same page to see updated data

    # Fetch all owner data from Firebase
    owners_data = db.child("owners").get().val()
    
    # Filter owners with 'accountStatus' set to 'disabled' and extract specified fields
    disabled_owners = []
    if owners_data:
        for email_key, owner_info in owners_data.items():
            if owner_info.get('accountStatus') == 'disabled':
                # Build the owner dictionary with only the needed fields
                owner = {
                    "email": email_key.replace('_at_', '@').replace('_', '.'),  # Convert back to email format
                    "firstname": owner_info.get("firstname", ""),
                    "middlename": owner_info.get("middlename", ""),
                    "lastname": owner_info.get("lastname", ""),
                    "gender": owner_info.get("gender", ""),
                    "address": owner_info.get("address", ""),
                    "accountStatus": owner_info.get("accountStatus", ""),
                    "profile_picture": owner_info.get("profile_picture", "")
                }
                disabled_owners.append(owner)
    
    # Add the list of disabled owners to context
    context['disabled_owners'] = disabled_owners
    context['active_page'] = 'undo'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 
    
    # Pass the context to the template
    return render(request, 'sao-DisabledOwners.html', context)


def removestudents(request): 
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Handle form submission to restore student account
    if request.method == "POST" and request.POST.get('action') == 'restore':
        student_email = request.POST.get('email')
        student_role = request.POST.get('studentRole')  # Capture the student role
        email_key = student_email.replace('.', '_').replace('@', '_at_')
        
        # Fetch student data and update accountStatus and role
        student_ref = db.child("students").child(email_key)
        student_ref.update({
            "accountStatus": "approved",
            "role": student_role  # Update role to 'student'
        })
        
        messages.success(request, f'Account of {student_email} has been restored and approved.')
        return redirect('removestudents')  # Redirect to the same page to see updated data

    # Fetch all student data from Firebase
    students_data = db.child("students").get().val()
    
    # Filter students with 'accountStatus' set to 'removed' and extract specified fields
    removed_students = []
    if students_data:
        for email_key, student_info in students_data.items():
            if student_info.get('accountStatus') == 'removed':
                # Build the student dictionary with only the needed fields
                student = {
                    "email": email_key.replace('_at_', '@').replace('_', '.'),
                    "username": student_info.get("username", ""),
                    "course": student_info.get("course", ""),
                    "gender": student_info.get("gender", ""),
                    "profile_picture": student_info.get("profile_picture", ""),
                    "accountStatus": student_info.get("accountStatus", ""),
                    "student_id": student_info.get("student_id", "")
                }
                removed_students.append(student)
    
    # Add the list of removed students to context
    context['removed_students'] = removed_students
    context['active_page'] = 'undo'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 
    
    # Pass the context to the template
    return render(request, 'sao-RemovedStudents.html', context)


def removeowners(request):  
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Handle form submission to restore owner account
    if request.method == "POST" and request.POST.get('action') == 'restore':
        owner_email = request.POST.get('email')
        owners_role = request.POST.get('ownersRole')  # Retrieve the role from hidden input
        email_key = owner_email.replace('.', '_').replace('@', '_at_')
        
        # Fetch owner data and update accountStatus and role
        owner_ref = db.child("owners").child(email_key)
        owner_ref.update({
            "accountStatus": "approved",
            "role": owners_role  # Update the role based on hidden input
        })
        boardinghouse_ref = db.child("ownersBoardingHouse").child(email_key)
        boardinghouse_ref.update({"boardinghouseStatus": "approved"})
        
        messages.success(request, f'Account of {owner_email} has been restored and approved.')
        return redirect('removeowners')  # Redirect to the same page to see updated data

    # Fetch all owner data from Firebase
    owners_data = db.child("owners").get().val()
    
    # Filter owners with 'accountStatus' set to 'removed' and extract specified fields
    removed_owners = []
    if owners_data:
        for email_key, owner_info in owners_data.items():
            if owner_info.get('accountStatus') == 'removed':
                # Build the owner dictionary with only the needed fields
                owner = {
                    "email": email_key.replace('_at_', '@').replace('_', '.'),
                    "firstname": owner_info.get("firstname", ""),
                    "middlename": owner_info.get("middlename", ""),
                    "lastname": owner_info.get("lastname", ""),
                    "gender": owner_info.get("gender", ""),
                    "address": owner_info.get("address", ""),
                    "accountStatus": owner_info.get("accountStatus", ""),
                    "profile_picture": owner_info.get("profile_picture", "")
                }
                removed_owners.append(owner)
    
    # Add the list of removed owners to context
    context['removed_owners'] = removed_owners
    context['active_page'] = 'undo'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 
    
    # Pass the context to the template
    return render(request, 'sao-RemovedOwners.html', context)


def removesao(request): 
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    

    # Fetch all superadmin data from Firebase
    superadmin_data = db.child("saoaccounts").child("datas").child("superadmin").get().val()
    
    # Filter students with 'accountStatus' set to 'removed' and extract specified fields
    removed_sao = []
    if superadmin_data:
        for superadmin_key, superadmin_info in superadmin_data.items():
            if superadmin_info.get('accountStatus') == 'removed':
                # Build the student dictionary with only the needed fields
                sao = {
                    "email": superadmin_key.replace('_at_', '@').replace('_', '.'),
                    "name": superadmin_info.get("name", ""),
                    "birthday": superadmin_info.get("birthday", ""),
                    "daysLogin": superadmin_info.get("daysLogin", ""),
                    "accountStatus": superadmin_info.get("accountStatus", ""),
                }
                removed_sao.append(sao)
    
    # Add the list of removed students to context
    context['removed_sao'] = removed_sao
    context['active_page'] = 'undo'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 
    
    # Pass the context to the template
    return render(request, 'sao-RemovedSAO.html', context)



def get_summary_counts():
    # Initialize counts for each category
    counts = {
        "disabled_students": 0,
        "disabled_owners": 0,
        "rejected_students": 0,
        "rejected_owners": 0,
        "removed_students": 0,
        "removed_owners": 0,
        "removed_sao": 0,  # Added for removed SAO accounts
    }

    try:
        # Fetch and process student data
        students_data = db.child("students").get().val()
        if isinstance(students_data, dict):
            for student_info in students_data.values():
                if student_info.get("accountStatus") == "disabled":
                    counts["disabled_students"] += 1
                elif student_info.get("accountStatus") == "rejected":
                    counts["rejected_students"] += 1
                elif student_info.get("accountStatus") == "removed":
                    counts["removed_students"] += 1

        # Fetch and process owner data
        owners_data = db.child("owners").get().val()
        if isinstance(owners_data, dict):
            for owner_info in owners_data.values():
                if owner_info.get("accountStatus") == "disabled":
                    counts["disabled_owners"] += 1
                elif owner_info.get("accountStatus") == "rejected":
                    counts["rejected_owners"] += 1
                elif owner_info.get("accountStatus") == "removed":
                    counts["removed_owners"] += 1

        # Fetch and process SAO data (superadmins)
        superadmin_data = db.child("saoaccounts").child("datas").child("superadmin").get().val()
        if isinstance(superadmin_data, dict):
            for superadmin_info in superadmin_data.values():
                if superadmin_info.get("accountStatus") == "removed":
                    counts["removed_sao"] += 1  # Count removed SAOs

    except Exception as e:
        print(f"Error fetching summary counts: {str(e)}")

    return counts





 



#This is for SAO 
def add_student(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/saohomepage/add_student")
    
    # Ensure that SAO PIN was verified before accessing this page
    if not request.session.get('sao_pincode_verified', False):
        messages.error(request, 'Please enter the correct SAO PIN to access this page.')
        return redirect('saohomepage')  # Redirect back to homepage if PIN is not verified

    # Get the SAO context
    context = get_sao_context(request)

    # Check if the email is present in the context
    if context is None or 'email' not in context:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to the login page if email is missing

    email = context['email']  # Extract email from context

    # Fetch the superadmin data specific to the logged-in user
    superadmin_data = db.child('saoaccounts/datas/superadmin').order_by_child('email').equal_to(email).get()

    if not superadmin_data.each():
        messages.error(request, "Superadmin not found.")
        return redirect('addsuperadmin')  # Redirect to the same page if superadmin not found

    # Assuming the first item returned is the relevant user data
    user_data = superadmin_data.each()[0].val()

    # Fetch the stored PIN
    stored_pincode = str(user_data.get('studentdatabasePin', ''))

    # Change PIN functionality
    if request.method == 'POST' and 'current_pin' in request.POST and 'new_pin' in request.POST:
        current_pin = request.POST.get('current_pin')
        new_pin = request.POST.get('new_pin')

        # Check if the current PIN matches the stored PIN
        if current_pin != stored_pincode:
            messages.error(request, "Current PIN does not match the records.")
            return redirect('add_student')  # Redirect to the same page if PIN does not match

        # Update the PIN in the database
        db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_data.each()[0].key()).update({'studentdatabasePin': new_pin})
        
        messages.success(request, "PIN has been updated successfully.")
        return redirect('add_student')  # Redirect to the same page

    # Handle delete request
    if request.method == "POST" and "delete_student" in request.POST:
        student_id = request.POST.get("delete_student")
        try:
            # Remove student from Firebase
            db.child("studentdatabase").child("datas").child(student_id).remove()
            messages.success(request, f"Student with ID {student_id} deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting student: {str(e)}")
        return redirect('add_student')  # Redirect back to the add_student page

    # Handle CSV upload for bulk importing students 
    elif request.method == "POST" and "csv_file" in request.FILES:
        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid CSV file.")
            return redirect('add_student')

        try:
            # Read and decode the CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            for row in reader:
                student_id = row.get('student_id')
                birthday = row.get('birthday')
                course = row.get('course')

                # Ensure that student_id is valid
                if not student_id:
                    messages.error(request, f"Row skipped: Missing student_id - {row}")
                    continue

                # Prepare the student data
                student_data = {
                    'student_id': student_id,
                    'birthday': birthday,
                    'course': course,
                }

                # Add or update the student in the database
                try:
                    db.child("studentdatabase").child("datas").child(student_id).update(student_data)
                except Exception as e:
                    messages.error(request, f"Error saving row: {row}. Error: {str(e)}")

            messages.success(request, "CSV file uploaded and processed successfully.")
        except Exception as e:
            messages.error(request, f"Error processing CSV file: {str(e)}")

        return redirect('add_student')




    # Handle adding a new student or updating an existing one
    elif request.method == "POST" and "student_id" in request.POST:
        student_id = request.POST.get('student_id')
        birthday = request.POST.get('birthday')
        course = request.POST.get('course')
        is_update = 'updateData' in request.POST  # Check if update button was clicked

        # Validate student_id format: Check if it starts with '72' and is exactly 7 digits
        if not re.match(r"^72\d{5}$", student_id):
            messages.error(request, "Student ID must start with '72' and be exactly 7 digits.")
            return redirect('add_student')

        # Validate birthday: it must be between 1974 and 2010
        try:
            birthday_date = datetime.strptime(birthday, '%Y-%m-%d')
            if birthday_date.year < 1974 or birthday_date.year > 2010:
                messages.error(request, "Birthday must be between 1974 and 2010.")
                return redirect('add_student')
        except ValueError:
            messages.error(request, "Invalid date format for birthday. Please use YYYY-MM-DD.")
            return redirect('add_student')

        # If it's an update and the student_id is being changed, check if the new student_id exists
        if is_update:
            existing_student = db.child("studentdatabase").child("datas").child(student_id).get().val()
            if not existing_student:
                messages.error(request, "The student ID does not exist. Cannot update student with a non-existing ID.")
                return redirect('add_student')

            # Update student data
            student_data = {
                'student_id': student_id,
                'birthday': birthday,
                'course': course,
            }

            try:
                db.child("studentdatabase").child("datas").child(student_id).update(student_data)
                messages.success(request, f"Student with ID {student_id} updated successfully.")
            except Exception as e:
                messages.error(request, f"Error updating student: {str(e)}")
        
        else:
            # Adding new student, check if student_id already exists
            existing_student = db.child("studentdatabase").child("datas").child(student_id).get().val()
            if existing_student:
                messages.error(request, "Student ID already exists. Cannot add duplicate student.")
                return redirect('add_student')

            # Add new student data
            student_data = {
                'student_id': student_id,
                'birthday': birthday,
                'course': course,
            }
            try:
                db.child("studentdatabase").child("datas").child(student_id).set(student_data)
                messages.success(request, f"Student with ID {student_id} added successfully.")
            except Exception as e:
                messages.error(request, f"Error adding student: {str(e)}")

        return redirect('add_student')  # Redirect back to the add_student page

    # Retrieve all students
    students = db.child("studentdatabase").child("datas").get().val()
    
    # Check if there is any data in the database and convert it to a list if necessary
    if students:
        students_list = list(students.values())  # Extract the list of students
        total_students = len(students_list)  # Get the total number of students

        # Count the occurrences of each course
        course_counts = Counter(student['course'] for student in students_list if 'course' in student)

        # Find the most popular course
        if course_counts:
            popular_course, _ = course_counts.most_common(1)[0]
        else:
            popular_course = "N/A"
    else:
        students_list = []  # Empty list if no students are present
        total_students = 0
        popular_course = "N/A"

    # Add the list of students, total count, and popular course to the context
    context['students'] = students_list
    context['total_students'] = total_students
    context['popular_course'] = popular_course

    # Add data for updating (if any)
    if 'update_student_id' in request.GET:  # Check if a student is being edited
        student_to_edit = db.child("studentdatabase").child("datas").child(request.GET['update_student_id']).get().val()
        context['student_to_edit'] = student_to_edit

    # Render the template with the updated context
    return render(request, 'add_student.html', context)



def download_csv(request):
    # Retrieve all student data
    students = db.child("studentdatabase").child("datas").get().val()

    if not students:
        messages.error(request, "No data available to download.")
        return redirect('add_student')

    # Prepare CSV data
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students_data.csv"'

    writer = csv.writer(response)
    # Write the header
    writer.writerow(['student_id', 'birthday', 'course'])

    # Write student data
    for student_id, student_data in students.items():
        writer.writerow([student_data.get('student_id'), student_data.get('birthday'), student_data.get('course')])

    return response


def addsuperadmin(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/saohomepage/addsuperadmin")
    # Ensure that SAO PIN was verified before accessing this page
    if not request.session.get('sao_pincode_verified', False):
        messages.error(request, 'Please enter the correct SAO PIN to access this page.')
        return redirect('saohomepage')

    # Get the SAO context
    context = get_sao_context(request)
    
    # Check if the email is present in the context
    if context is None or 'email' not in context:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to the login page if email is missing

    email = context['email']  # Extract email from context

    # Change PIN functionality
    if request.method == 'POST' and 'current_pin' in request.POST and 'new_pin' in request.POST:
        current_pin = request.POST.get('current_pin')
        new_pin = request.POST.get('new_pin')

        # Fetch the superadmin data specific to the logged-in user
        superadmin_data = db.child('saoaccounts/datas/superadmin').order_by_child('email').equal_to(email).get()

        if not superadmin_data.each():
            messages.error(request, "Superadmin not found.")
            return redirect('addsuperadmin')  # Redirect to the same page

        # Assuming the first item returned is the relevant user data
        user_data = superadmin_data.each()[0].val()

        # Fetch the stored PIN
        stored_pincode = str(user_data.get('addsuperadminPin', ''))

        # Check if the current PIN matches the stored PIN
        if current_pin != stored_pincode:
            messages.error(request, "Current PIN does not match the records.")
            return redirect('addsuperadmin')  # Redirect to the same page

        # Update the PIN in the database
        db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_data.each()[0].key()).update({'addsuperadminPin': new_pin})
        
        messages.success(request, "PIN has been changed successfully.")
        return redirect('addsuperadmin')  # Redirect to the same page

    # Check if removal request is present
    if request.method == 'POST' and 'remove_email' in request.POST:
        email_to_remove = request.POST.get('remove_email')
        email_key = email_to_remove.replace('.', '_').replace('@', '_at_')

        # Create a removal request
        removal_request_data = {
            'requested_by': email,  # Use the email from context
            'email': email_to_remove,
            'status': 'pending'  # Status can be 'pending', 'approved', or 'disapproved'
        }

        try:
            # Add the removal request to the database
            db.child("saoaccounts").child("datas").child("removal_requests").child(email_key).set(removal_request_data)
            
            # Update the superadmin's account status to 'removed'
            superadmin_data = db.child("saoaccounts").child("datas").child("superadmin").order_by_child('email').equal_to(email_to_remove).get()

            if superadmin_data.each():
                superadmin_key = superadmin_data.each()[0].key()  # Get the key of the superadmin (e.g., 'superadmin1')
                db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_key).update({'accountStatus': 'removing'})
                messages.success(request, f"A removal request has been submitted, voting for removal is now open. View Homepage.")
            else:
                messages.error(request, f"No superadmin found with email {email_to_remove}.")
                
        except Exception as e:
            messages.error(request, f"Error submitting removal request: {str(e)}")



    # Handle adding a new superadmin
    elif request.method == 'POST' and 'email' in request.POST:
        new_superadmin_email = request.POST.get('email')
        birthday = request.POST.get('birthday')

        # Validate birthday year
        try:
            birth_year = datetime.strptime(birthday, '%Y-%m-%d').year
            if birth_year < 1924 or birth_year > 2015:
                messages.error(request, 'Invalid birthday. The year must be between 1924 and 2015.')
                return render(request, 'add_sao.html', context)
        except ValueError:
            messages.error(request, 'Invalid date format. Please enter the date in YYYY-MM-DD format.')
            return render(request, 'add_sao.html', context)

        # Generate PIN codes
        def generate_pincode():
            return str(random.randint(10000, 99999))

        studentdatabasePin = generate_pincode()
        addsuperadminPin = generate_pincode()

        # Get existing superadmins for incremental naming
        existing_superadmins = db.child("saoaccounts").child("datas").child("superadmin").get().val()

        if existing_superadmins:
            valid_keys = [key for key in existing_superadmins.keys() if key.startswith('superadmin')]
            if valid_keys:
                highest_number = max(int(key.replace('superadmin', '')) for key in valid_keys)
                new_superadmin_name = f"superadmin{highest_number + 1}"
            else:
                new_superadmin_name = "superadmin1"
        else:
            new_superadmin_name = "superadmin1"

        # Prepare superadmin data with default password and PIN codes
        superadmin_data = {
            'email': new_superadmin_email,
            'birthday': birthday,
            'password': 'ctuacaccreditedboardinghouse',
            'name': new_superadmin_name,
            'role': "superadmin",
            'active_status': "offline",
            'accountStatus': "approved",
            'studentdatabasePin': studentdatabasePin,
            'addsuperadminPin': addsuperadminPin,
            'signup_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Store current date and time
            'daysLogin': 0  # Initialize daysLogin to 0
        }

        try:
            # Create the user in Firebase Authentication
            auth_instance.create_user_with_email_and_password(new_superadmin_email, superadmin_data['password'])
            db.child("saoaccounts").child("datas").child("superadmin").child(new_superadmin_name).set(superadmin_data)

            # Send password reset email
            auth_instance.send_password_reset_email(new_superadmin_email)

            # Prepare the HTML email content for PINs with reset link
            email_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                    .card {{ background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); max-width: 600px; margin: auto; padding: 20px; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ margin: 20px 0; font-size: 16px; line-height: 1.5; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 14px; color: #555; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="header">
                        <h2>Superadmin Account Creation</h2>
                    </div>
                    <center><img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo" style="width: 50%; height: auto;"></center>
                    <div class="content">
                        <p>A password reset link has been sent to {new_superadmin_email}. Please check your inbox to create your own password.</p>
                        <p>Your Student Database PIN is: <strong>{studentdatabasePin}</strong></p>
                        <p>Your Add Superadmin PIN is: <strong>{addsuperadminPin}</strong></p>
                    </div>
                    <div class="footer">
                        <p>Thank you for using our service!</p> 
                        <p>The Datalink Team</p> 
                    </div>
                </div>
            </body>
            </html>
            """

            # Send email with PIN codes
            send_mail(
                'Superadmin Account Creation',
                '', 
                'your_email@example.com',
                [new_superadmin_email],
                fail_silently=False,
                html_message=email_content
            )

            # Clear the default password in Realtime Database
            db.child("saoaccounts").child("datas").child("superadmin").child(new_superadmin_name).update({'password': None})

            messages.success(request, f"A password reset link has been sent to {new_superadmin_email}. Please check your inbox to create your own password.")

        except Exception as e:
            error_message = str(e)
            if 'EMAIL_EXISTS' in error_message:
                messages.error(request, "The email address is already registered. Please use a different email.")
            else:
                messages.error(request, f"Failed to send password reset link or save superadmin data: {error_message}")

    # Fetch and display superadmins
    try:
        superadmins = db.child("saoaccounts").child("datas").child("superadmin").get().val()
        superadmin_list = []

        if superadmins:
            for saoid, data in superadmins.items():
                if 'email' in data and data.get('role') == 'superadmin' and data.get('accountStatus') == 'approved':  # Filter by 'approved' status
                    superadmin_list.append({
                        'SAOID': saoid,
                        'email': data.get('email'),
                        'birthday': data.get('birthday'),
                        'role': data.get('role', 'superadmin')
                    })

    except Exception as e:
        messages.error(request, f"Error fetching superadmin data: {str(e)}")
        superadmin_list = []

    return render(request, 'add_sao.html', {
        'superadmin_list': superadmin_list,
        **context,
    })










def sao_login(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/sao_login")
    email = ""  # Initialize email variable

    if request.method == 'POST':
        email = request.POST.get('email')  # Get the email from the POST request
        password = request.POST.get('password')

        try:
            # Authenticate user with Firebase
            user = auth_instance.sign_in_with_email_and_password(email, password)

            # Fetch user data from Realtime Database to check the role and get the superadmin name
            user_data = db.child("saoaccounts").child("datas").child("superadmin").order_by_child("email").equal_to(email).get()

            if user_data.each():
                user_info = user_data.each()[0].val()  # Get the first matching user data

                # Check if the fetched user has the same email
                if user_info.get('email') == email:
                    role = user_info.get('role')
                    name = user_info.get('name')  # Assuming "name" field exists in the database
                    superadmin_name = user_info.get('name')  # This should match how you saved the name

                    if role == "superadmin":
                        # Store name and email in session
                        request.session['name'] = name
                        request.session['email'] = email

                        # Set active_status to 'online' in Firebase Realtime Database using the saved key
                        db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_name).update({"active_status": "online"})

                        # Generate a 6-digit OTP
                        otp = random.randint(100000, 999999)
                        otp_expiry = datetime.now() + timedelta(minutes=10)  # OTP valid for 10 minutes

                        # Send OTP to the user's email with styled HTML content
                        subject = 'Your OTP for SAO Login'
                        email_content = f"""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <style>
                                body {{
                                    font-family: Arial, sans-serif;
                                    background-color: #f5f5f5;
                                    margin: 0;
                                    padding: 20px;
                                }}
                                .card {{
                                    background-color: #ffffff;
                                    border-radius: 8px;
                                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                                    max-width: 600px;
                                    margin: auto;
                                    overflow: hidden;
                                    padding: 20px;
                                }}
                                .header {{
                                    background-color: #007bff;
                                    color: white;
                                    padding: 20px;
                                    text-align: center;
                                }}
                                .content {{
                                    margin: 20px 0;
                                    font-size: 16px;
                                    line-height: 1.5;
                                }}
                                .footer {{
                                    text-align: center;
                                    margin-top: 20px;
                                    font-size: 14px;
                                    color: #555;
                                }}
                                .button {{
                                    display: inline-block;
                                    background-color: #007bff;
                                    color: white;
                                    padding: 10px 20px;
                                    text-decoration: none;
                                    border-radius: 5px;
                                    font-weight: bold;
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="card">
                                <div class="header">
                                    <h2>Your OTP for SAO Login</h2>
                                </div>
                                <center><img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo" style="width: 50%; height: auto;"></center>
                                <div class="content">
                                    <p>Your One-Time Password (OTP) for SAO login is <strong>{otp}</strong>. It is valid for 10 minutes.</p>
                                    <p>If you did not request this OTP, please ignore this email.</p>
                                </div>
                                <div class="footer">
                                    <p>Thank you for using our service!</p>
                                </div>
                            </div>
                        </body>
                        </html>
                        """
                        from_email = 'your_email@example.com'  # Replace with your actual email
                        recipient_list = [email]
                        send_mail(subject, '', from_email, recipient_list, fail_silently=False, html_message=email_content)

                        # Store OTP and expiry in session
                        request.session['otp'] = otp
                        request.session['otp_expiry'] = otp_expiry.strftime('%Y-%m-%d %H:%M:%S')

                        # Redirect to OTP verification page
                        messages.success(request, 'OTP has been sent to your email.')
                        return redirect('sao_verify_otp')
                    else:
                        messages.error(request, 'Access denied. You are not authorized to log in as a superadmin.')
            else:
                messages.error(request, 'User not found.')

        except Exception as e:
            print(str(e))  # Log the error for debugging
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'SAOLOGIN.html', {'email': email})  # Ensure email is passed when rendering




def sao_verify_otp(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path 

    if request.method == 'POST':
        # Collect OTP digits from separate inputs
        otp_digits = [
            request.POST.get('otp1', ''),
            request.POST.get('otp2', ''),
            request.POST.get('otp3', ''),
            request.POST.get('otp4', ''),
            request.POST.get('otp5', ''),
            request.POST.get('otp6', '')
        ]
        
        # Join the OTP digits into a single string
        otp = ''.join(otp_digits)
        
        stored_otp = request.session.get('otp')
        otp_expiry = request.session.get('otp_expiry')
        
        if otp and stored_otp and otp_expiry:
            # Check if OTP is correct and not expired
            if otp == str(stored_otp) and datetime.strptime(otp_expiry, '%Y-%m-%d %H:%M:%S') > datetime.now():
                # OTP is correct and not expired
                email = request.session.get('email')
                name = request.session.get('name')
                
                # Clear OTP from session
                request.session.pop('otp', None)
                request.session.pop('otp_expiry', None)

                # Fetch the correct superadmin entry from Firebase based on the session-stored name or email
                user_data = db.child("saoaccounts").child("datas").child("superadmin").order_by_child("email").equal_to(email).get()
                
                if user_data.each():
                    user_info = user_data.each()[0]  # Get the first matching entry (should be the correct one)
                    superadmin_key = user_info.key()  # Get the key for the superadmin account
                    
                    # Retrieve the current daysLogin value
                    current_days_login = user_info.val().get('daysLogin', 0)

                    # Increment the daysLogin by 1
                    new_days_login = current_days_login + 1

                    # Update active_status and daysLogin in Firebase Realtime Database using the correct key
                    db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_key).update({
                        "active_status": "online",
                        "daysLogin": new_days_login  # Update the daysLogin field
                    })

                    # Log the IP and URL with additional user data
                    user_role = user_info.val().get("role", "unknown")  # Fetch role safely
                    log_ip_and_url(ip_address, current_url, "sao/sao_login/sao_verify_otp/", user_email=email, user_status="online", user_role=user_role)
                    
                    # Redirect to the homepage or any protected page 
                    messages.success(request, f'Successfully logged in as {name}.')
                    return redirect('saohomepage')  # Redirect to the desired page after OTP verification
                else:
                    messages.error(request, 'User not found in the database.')
            else:
                messages.error(request, 'Invalid or expired OTP.')
        else:
            messages.error(request, 'OTP verification failed.')

    # Log IP and URL in case of GET or failed POST
    log_ip_and_url(ip_address, current_url, "sao/sao_login/sao_verify_otp/")

    return render(request, 'sao_otplogin.html')



def demoAddStudent(request):
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing
    return render(request, 'demoForAddStudent.html', context)


def demoAddSAO(request):
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing
    return render(request, 'demoForAddSAO.html', context)


def usermonitoring(request):
    context = get_sao_context(request)

    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Fetch data from 'fetchedusersIPaddress' path in Firebase
    users_data = db.child('fetchedusersIPaddress').get()

    users = []
    active_users_count = 0  # Counter for active users
    inactive_users_count = 0  # Counter for inactive users
    student_count = 0  # Counter for students
    superadmin_count = 0  # Counter for superadmins
    owner_count = 0  # Counter for owners
    unknown_count = 0  # Counter for unknown users
    
    if users_data and users_data.each():
        for item in users_data.each():
            user_info = item.val()
            user = {
                'ip': user_info.get('ip'),
                'last_visited': user_info.get('last_visited'),
                'urls_visited': user_info.get('urls_visited', []),
                'identity': user_info.get('identity', 'Unknown'),
                'active_status': user_info.get('active_status', 'Unknown'),
                'role': user_info.get('role', 'Unknown'),
            }
            users.append(user)

            # Increment the counters based on the active status
            if user_info.get('active_status') == "Active":
                active_users_count += 1
            elif user_info.get('active_status') == "Inactive":
                inactive_users_count += 1

            # Count users based on their role
            role = user_info.get('role', 'Unknown')
            if role == "student":
                student_count += 1
            elif role == "superadmin":
                superadmin_count += 1
            elif role == "owner":
                owner_count += 1
            elif role == "Unknown":
                unknown_count += 1

    print("Fetched Users:", users)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Return the user data and counts as JSON for AJAX requests
        return JsonResponse({
            'users': users,
            'active_users_count': active_users_count,
            'inactive_users_count': inactive_users_count,
            'student_count': student_count,
            'superadmin_count': superadmin_count,
            'owner_count': owner_count,
            'unknown_count': unknown_count,
        })

    # Add all counts to the context
    context['user_data_list'] = users
    context['active_users_count'] = active_users_count
    context['inactive_users_count'] = inactive_users_count
    context['student_count'] = student_count
    context['superadmin_count'] = superadmin_count
    context['owner_count'] = owner_count
    context['unknown_count'] = unknown_count

    return render(request, 'usersMonitor.html', context)














def sao_forgotpassword(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/sao_forgotpassword/")
    if request.method == 'POST':
        email = request.POST.get('email')
        birthday = request.POST.get('birthday')

        # Fetch superadmin data from Firebase
        existing_superadmins = db.child("saoaccounts").child("datas").child("superadmin").get().val()

        # Debugging: Print existing superadmins data
        print("Existing superadmins:", existing_superadmins)

        # Check if superadmins exist
        if not existing_superadmins:
            error_message = "Superadmin account not found."
            return render(request, 'sao_forgotpassword.html', {'error_message': error_message})

        # Check if the provided email and birthday match any superadmin
        for superadmin_name, superadmin_data in existing_superadmins.items():
            # Debugging: Print superadmin data for each entry
            print(f"Checking {superadmin_name}: {superadmin_data}")
            
            # Ensure 'email' and 'birthday' keys exist in superadmin_data
            if 'email' in superadmin_data and 'birthday' in superadmin_data:
                if superadmin_data['email'] == email and superadmin_data['birthday'] == birthday:
                    try:
                        # Send password reset email using Pyrebase
                        auth_instance.send_password_reset_email(email)
                        success_message = f"A password reset link has been sent to {email}."
                        return render(request, 'sao_forgotpassword.html', {'success_message': success_message})
                    except Exception as e:
                        error_message = f"An error occurred while sending the reset email: {str(e)}"
                        return render(request, 'sao_forgotpassword.html', {'error_message': error_message})
            else:
                print(f"Missing keys in superadmin_data: {superadmin_data}")

        error_message = "Superadmin account not found."
        return render(request, 'sao_forgotpassword.html', {'error_message': error_message})

    return render(request, 'sao_forgotpassword.html')




def get_sao_context(request):
    #greeting = get_greeting()
    # Retrieve name and email from session
    name = request.session.get('name', 'Guest')  # Default to 'Guest' if the name is not found
    email = request.session.get('email')
    active_status = 'offline'  # Default to offline
    birthday = None  # Initialize birthday as None
    pending_students_count = 0  # Count for pending students
    pending_owners_count = 0  # Count for pending owners
    total_pending_count = 0  # Total count of pending students and owners
    unfixed_students_count = 0  # Count for students with 'unfixed' status
    unfixed_owners_count = 0  # Count for owners with 'unfixed' status
    days_login = 0  # Default daysLogin

    if not email:
        return None  # If email is not found, return None

    try:
        # Fetch all superadmins from Firebase
        existing_superadmins = db.child("saoaccounts").child("datas").child("superadmin").get().val()

        # Loop through all superadmins to find the matching email
        if existing_superadmins:
            for superadmin_key, superadmin_data in existing_superadmins.items():
                if superadmin_data.get('email') == email:
                    # Fetch active status, birthday, and daysLogin
                    active_status = superadmin_data.get('active_status', 'offline')
                    birthday = superadmin_data.get('birthday', None)  # Fetch the birthday from Firebase
                    name = superadmin_data.get('name', name)  # Update the name from Firebase if available
                    days_login = superadmin_data.get('daysLogin', 0)  # Fetch the daysLogin value
                    break
        else:
            print("No superadmin data found.")
            active_status = 'offline'

        # Fetch pending students count
        students_data = db.child("students").get().val()
        if students_data:
            for student_email, student_data in students_data.items():
                if student_data.get('accountStatus') == 'pending':
                    pending_students_count += 1
                if student_data.get('status') == 'unfixed':  # Check for 'unfixed' status
                    unfixed_students_count += 1

        # Fetch pending owners count
        owners_data = db.child("owners").get().val()
        if owners_data:
            for owner_email, owner_data in owners_data.items():
                if owner_data.get('accountStatus') == 'pending':
                    pending_owners_count += 1
                if owner_data.get('status') == 'unfixed':  # Check for 'unfixed' status
                    unfixed_owners_count += 1

        # Fetch owner reports and student reports from messages path
        owner_reports = db.child("usersReport").child("owners").get().val()
        student_reports = db.child("usersReport").child("students").get().val()

        # Count owners with 'unfixed' status in the reports
        if owner_reports:
            for owner_email, owner_data in owner_reports.items():
                for message_id, message_data in owner_data.get('messages', {}).items():
                    if message_data.get('status') == 'unfixed':
                        unfixed_owners_count += 1

        # Count students with 'unfixed' status in the reports
        if student_reports:
            for student_email, student_data in student_reports.items():
                for message_id, message_data in student_data.get('messages', {}).items():
                    if message_data.get('status') == 'unfixed':
                        unfixed_students_count += 1

        # Calculate the total pending count (students + owners)
        total_pending_count = pending_students_count + pending_owners_count

    except Exception as e:
        # Handle any errors with fetching data
        print(f"Error fetching SAO data from Firebase: {e}")

    # Prepare context dictionary
    context = {
        'name': name,
        'email': email,
        'active_status': active_status,
        'birthday': birthday,  # Include birthday in the context
        'pending_students_count': pending_students_count,  # Include count of pending students
        'pending_owners_count': pending_owners_count,  # Include count of pending owners
        'total_pending_count': total_pending_count,  # Include total count of pending students and owners
        'unfixed_students_count': unfixed_students_count,  # Include count of students with 'unfixed' status
        'unfixed_owners_count': unfixed_owners_count,  # Include count of owners with 'unfixed' status
        'daysLogin': days_login,  # Include daysLogin in the context
        #'greeting': greeting,
    }

    return context


@csrf_exempt  # Only if CSRF token is manually handled in the script
def update_days_login_sao(request):
    if request.method == 'POST':
        try:
            # Use get_sao_context to fetch the SAO's context
            sao_context = get_sao_context(request)
            if not sao_context:
                return JsonResponse({'error': 'SAO context could not be retrieved'}, status=400)

            # Extract email from the context
            email = sao_context.get('email')
            if not email:
                return JsonResponse({'error': 'Email not found in context'}, status=400)

            # Generate Firebase key
            email_key = email.replace('.', '_').replace('@', '_at_')

            # Fetch the list of superadmins from Firebase
            superadmins_data = db.child("saoaccounts").child("datas").child("superadmin").get().val()
            if not superadmins_data:
                return JsonResponse({'error': 'Superadmin data not found in Firebase'}, status=404)

            # Loop through superadmin data to find the matching email
            for superadmin_key, superadmin_data in superadmins_data.items():
                if superadmin_data.get('email') == email:
                    # Update the `daysLogin` field in Firebase for the matching superadmin
                    db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_key).update(
                        {'daysLogin': sao_context['daysLogin'] + 1}
                    )
                    messages.success(request, "Tour is complete! Welcome Superadmin, you can now work your progress.")
                    return JsonResponse({'message': 'daysLogin updated successfully'})

            # If no matching email is found
            return JsonResponse({'error': 'Superadmin email not found in the superadmin list'}, status=404)

        except Exception as e:
            # Handle errors gracefully
            return JsonResponse({'error': str(e)}, status=500)

    # Return a method not allowed response if the request is not POST
    return JsonResponse({'error': 'Invalid request method'}, status=405)





def saohomepage(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/saohomepage")
    # Constants (inside the function)
    MAX_ATTEMPTS = 3
    INITIAL_LOCKOUT_TIME = 5  # in minutes
    LOCKOUT_INCREMENT = 5  # increment time in minutes for each subsequent lockout
     
    # Get the SAO context
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Specific active page for homepage
    context['active_page'] = 'dashboard'
    total_pending_accounts = count_pending_accounts()
    summary_counts = get_summary_counts()
    context.update({
        'total_pending_accounts': total_pending_accounts,
        'summary_counts': get_summary_counts,
    }) 

    email = request.session.get('email')  # Get the email from session

    # Fetch all students with accountStatus of "approved"
    try:
        # Fetch approved students
        approved_students = db.child("students").order_by_child("accountStatus").equal_to("approved").get()
        approved_student_list = []

        # Check if there are any students found
        if approved_students.each():
            for student in approved_students.each():
                student_data = student.val()  # Get the student data
                approved_student_list.append(student_data)

        # Add approved students to context
        context['approved_students'] = approved_student_list
        context['approved_student_count'] = len(approved_student_list)  # Count of approved students
        print(f"Found {len(approved_student_list)} approved students.")  # Debugging line

        # Fetch all owners with accountStatus as "approved"
        approved_owners = db.child("owners").order_by_child("accountStatus").equal_to("approved").get()
        approved_owner_list = []

        # Check if there are any owners found
        if approved_owners.each():
            for owner in approved_owners.each():
                owner_data = owner.val()  # Get the owner data
                approved_owner_list.append(owner_data)

        # Add approved owners to context
        context['approved_owners'] = approved_owner_list
        context['approved_owner_count'] = len(approved_owner_list)  # Count of approved owners
        print(f"Found {len(approved_owner_list)} approved owners.")  # Debugging line

        # Total count of approved students and approved owners
        context['total_approved_count'] = len(approved_student_list) + len(approved_owner_list)

    except Exception as e:
        print(f"Error fetching approved users: {str(e)}")
        messages.error(request, f"Error fetching approved users: {str(e)}")

        
    # Handle student PIN submission
    if request.method == 'POST' and 'student_pincode' in request.POST:
        entered_pincode = request.POST.get('student_pincode', '')
        
        # Fetch lockout data from the session or initialize it
        lockout_data = request.session.get(f'lockout_data_{email}_student', {
            'attempts': 0,
            'lockout_until': None,
            'lockout_time': INITIAL_LOCKOUT_TIME
        })
        
        # Check if the user is locked out
        if lockout_data['lockout_until']:
            lockout_until = datetime.fromisoformat(lockout_data['lockout_until'])
            if datetime.now() < lockout_until:
                remaining_time = (lockout_until - datetime.now()).total_seconds() // 60
                messages.error(request, f'You are locked out. Try again in {int(remaining_time)} minutes.')
                return render(request, 'SAO-Homepage.html', context)

        try:
            # Fetch the superadmin data specific to the logged-in user
            superadmin_data = db.child('saoaccounts/datas/superadmin').order_by_child('email').equal_to(email).get()

            if superadmin_data.each():
                user_data = superadmin_data.each()[0].val()

                # Get stored student PIN from the database
                stored_pincode = str(user_data.get('studentdatabasePin', ''))

                if entered_pincode == stored_pincode:
                    # Reset lockout data
                    lockout_data['attempts'] = 0
                    lockout_data['lockout_time'] = INITIAL_LOCKOUT_TIME
                    lockout_data['lockout_until'] = None
                    request.session[f'lockout_data_{email}_student'] = lockout_data

                    # Set session variable for PIN verification
                    request.session['sao_pincode_verified'] = True  # Use the consistent name
                    messages.success(request, 'Correct PIN entered!')
                    return redirect('add_student')
                else:
                    # Handle incorrect PIN
                    lockout_data['attempts'] += 1
                    if lockout_data['attempts'] >= MAX_ATTEMPTS:
                        lockout_data['lockout_until'] = (datetime.now() + timedelta(minutes=lockout_data['lockout_time'])).isoformat()
                        lockout_data['lockout_time'] += LOCKOUT_INCREMENT
                        messages.error(request, f'Incorrect PIN. You are locked out for {lockout_data["lockout_time"] - LOCKOUT_INCREMENT} minutes.')
                    else:
                        messages.error(request, f'Incorrect PIN. You have {MAX_ATTEMPTS - lockout_data["attempts"]} attempts left.')

                    request.session[f'lockout_data_{email}_student'] = lockout_data
            else:
                messages.error(request, "No data found in the database.")
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            messages.error(request, f"Error fetching data: {str(e)}")


    # Handle SAO PIN submission
    if request.method == 'POST' and 'superadmin_pincode' in request.POST:
        entered_pincode = request.POST.get('superadmin_pincode', '')
        
        # Fetch lockout data for SAO PIN
        lockout_data = request.session.get(f'lockout_data_{email}_sao', {
            'attempts': 0,
            'lockout_until': None,
            'lockout_time': INITIAL_LOCKOUT_TIME
        })

        # Check if the user is currently locked out
        if lockout_data['lockout_until']:
            lockout_until = datetime.fromisoformat(lockout_data['lockout_until'])
            if datetime.now() < lockout_until:
                remaining_time = (lockout_until - datetime.now()).total_seconds() // 60
                messages.error(request, f'You are locked out. Try again in {int(remaining_time)} minutes.')
                return render(request, 'SAO-Homepage.html', context)

        try:
            # Fetch the superadmin PIN specific to the logged-in user
            superadmin_data = db.child('saoaccounts/datas/superadmin').order_by_child('email').equal_to(email).get()

            if superadmin_data.each():
                user_data = superadmin_data.each()[0].val()  # Get the first matching superadmin data

                # Get stored SAO PIN from the database
                stored_pincode = str(user_data.get('addsuperadminPin', ''))

                if entered_pincode == stored_pincode:
                    # Reset lockout attempts
                    lockout_data['attempts'] = 0
                    lockout_data['lockout_time'] = INITIAL_LOCKOUT_TIME  # Reset to initial time
                    request.session[f'lockout_data_{email}_sao'] = lockout_data

                    # Set session variable for SAO PIN verification
                    request.session['sao_pincode_verified'] = True
                    messages.success(request, 'Correct SAO PIN entered!')
                    return redirect('addsuperadmin')  # Redirect if the PIN is correct
                else:
                    # Increment attempts and lockout logic
                    lockout_data['attempts'] += 1
                    if lockout_data['attempts'] >= MAX_ATTEMPTS:
                        lockout_data['lockout_until'] = (datetime.now() + timedelta(minutes=lockout_data['lockout_time'])).isoformat()
                        lockout_data['lockout_time'] += LOCKOUT_INCREMENT
                        messages.error(request, f'Incorrect PIN. You are locked out for {lockout_data["lockout_time"] - LOCKOUT_INCREMENT} minutes.')
                    else:
                        messages.error(request, f'Incorrect PIN. You have {MAX_ATTEMPTS - lockout_data["attempts"]} attempts left.')

                    # Save lockout data in session
                    request.session[f'lockout_data_{email}_sao'] = lockout_data

            else:
                messages.error(request, "No data found in the database.")

        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            messages.error(request, f"Error fetching data: {str(e)}")


    # Check for removal requests for the logged-in superadmin
    try:
        email_key = request.session.get('email').replace('.', '_').replace('@', '_at_')
        removal_requests = db.child("saoaccounts").child("datas").child("removal_requests").get()

        if removal_requests.each():
            context['removal_requests'] = [req.val() for req in removal_requests.each()]
        else:
            context['removal_requests'] = []

        # Count superadmins
        all_superadmins = db.child("saoaccounts").child("datas").child("superadmin").get()
        superadmin_list = [superadmin.val() for superadmin in all_superadmins.each()] if all_superadmins.each() else []
        context['superadmin_count'] = len(superadmin_list)

    except Exception as e:
        print(f"Error fetching removal requests: {str(e)}")
        messages.error(request, f"Error fetching removal requests: {str(e)}")

    
    if request.method == 'POST' and 'remove_superadmin' in request.POST:
        removal_email = request.POST.get('removal_email')
        action = request.POST.get('action')  # Either 'approve' or 'disapprove'

        try:
            # Process the email key
            email_key_to_remove = removal_email.replace('.', '_').replace('@', '_at_') 

            # Fetch user data from Realtime Database
            user_data = db.child("saoaccounts").child("datas").child("superadmin").order_by_child("email").equal_to(removal_email).get()

            if not user_data.each():
                messages.error(request, f"No superadmin found with email {removal_email}.")
                return

            superadmin_data = user_data.each()[0].val()
            superadmin_key = user_data.each()[0].key()  

            # Check for existing removal request data
            removal_request_data = db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).get()

            if not removal_request_data.val():
                db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).set({
                    'email': removal_email,
                    'votes': {
                        'approve': 0,
                        'reject': 0,
                    },
                    'status': 'pending',
                    'user_votes': {}  
                })
                removal_request_data = db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).get()

            current_votes = removal_request_data.val().get('votes', {'approve': 0, 'reject': 0})
            new_approve_count = current_votes.get('approve', 0)
            new_reject_count = current_votes.get('reject', 0)

            voting_user_email = request.session.get('email').replace('.', '_').replace('@', '_at_')

            # Check if the user has already voted
            user_votes = removal_request_data.val().get('user_votes', {})
            if voting_user_email in user_votes:
                # If the user has voted, remove their vote from user_votes
                previous_vote = user_votes[voting_user_email]

                # Update vote counts accordingly
                if previous_vote == 'approve':
                    new_approve_count -= 1
                elif previous_vote == 'disapprove':
                    new_reject_count -= 1

                # Remove the user's vote from user_votes
                db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).child('user_votes').child(voting_user_email).remove()

            # Increment votes based on the new action
            if action == 'approve':
                new_approve_count += 1
                db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).child('votes/approve').set(new_approve_count)
            elif action == 'disapprove':
                new_reject_count += 1
                db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).child('votes/reject').set(new_reject_count)
            
            # Store the user's new vote
            db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).child('user_votes').child(voting_user_email).set(action)

            # Calculate the majority rule
            total_votes = new_approve_count + new_reject_count
            if total_votes >= len(superadmin_list) // 2:
                if new_approve_count > new_reject_count:
                    db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_key).update({'role': 'removed', 'accountStatus': 'removed'})
                    db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).child('status').set('approved')
                    messages.success(request, f'Superadmin {removal_email} has been removed successfully.')
                else:
                    db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_key).update({'role': 'superadmin'})  
                    db.child("saoaccounts").child("datas").child("removal_requests").child(email_key_to_remove).child('status').set('disapproved')
                    messages.warning(request, 'Removal request did not achieve majority approval.')

        except Exception as e:
            print(f"Error processing removal request: {str(e)}")
            messages.error(request, f"Error processing removal request: {str(e)}")
 
 
    # Render homepage with the updated context
    return render(request, 'SAO-Homepage.html', context)



def count_pending_accounts():
    pending_students_count = 0
    pending_owners_count = 0

    # Count pending students
    try:
        all_students_data = db.child("students").get().val()
        if all_students_data:
            for student_key, student_data in all_students_data.items():
                if student_data.get('accountStatus') == "pending":
                    pending_students_count += 1
    except Exception as e:
        print(f"Error fetching pending students data: {str(e)}")

    # Count pending owners
    try:
        all_owners_data = db.child("owners").get().val()
        if all_owners_data:
            for owner_key, owner_data in all_owners_data.items():
                if owner_data.get('accountStatus') == "pending":
                    pending_owners_count += 1
    except Exception as e:
        print(f"Error fetching pending owners data: {str(e)}")

    # Total pending accounts
    return pending_students_count + pending_owners_count




def sao_delete_conversation(request, student_email):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/studenthomepage/sao_delete_conversation")
    
    superadmin_context = get_sao_context(request)
    if superadmin_context is None:  # User is not logged in
        return redirect('sao_login')

    # Sanitize email addresses
    sanitized_from_superadmin = sanitize_path_part(superadmin_context['email'])
    sanitized_student_email = sanitize_path_part(student_email)

    messages_path_1 = f'messages/{sanitized_from_superadmin}-{sanitized_student_email}'
    messages_path_2 = f'messages/{sanitized_student_email}-{sanitized_from_superadmin}'

    # Delete messages if they exist in either path
    messages_data_path_1 = db.child(messages_path_1).get()
    messages_data_path_2 = db.child(messages_path_2).get()

    if messages_data_path_1.val() is not None:
        db.child(messages_path_1).remove()
        print(f"Messages deleted successfully from: {messages_path_1}")
    elif messages_data_path_2.val() is not None:
        db.child(messages_path_2).remove()
        print(f"Messages deleted successfully from: {messages_path_2}")
    else:
        print(f"No messages found for deletion at paths: {messages_path_1} or {messages_path_2}")

    # Redirect back to the same conversation with the query parameter
    return redirect(f'/sao/saohomepage/sao_message?student_email={student_email}')





def sao_message(request):
    # Fetch superadmin context
    superadmin_context = get_sao_context(request)
    if superadmin_context is None:  # User is not logged in
        return redirect('sao_login')

    # Fetch student data from the database
    students_data = db.child('students').get()
    student_list = []

    if students_data and students_data.each():
        for item in students_data.each():
            student_info = {
                'email': item.val().get('email', 'No Email'),
                'username': item.val().get('username', 'No Username'),
                'student_id': item.val().get('student_id', 'No Student ID'),
                'profile_picture': item.val().get(
                    'profile_picture',
                    'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4'
                ),
                'active_status': item.val().get('active_status', 'offline'),
            }
            student_list.append(student_info)

    # Determine the selected student
    current_student_email = request.GET.get('student_email')
    selected_student = None
    if current_student_email:
        selected_student = next((student for student in student_list if student['email'] == current_student_email), None)

    # Initialize messages list
    messages = []

    # Handle AJAX request for fetching messages
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        sanitized_from_superadmin = sanitize_path_part(superadmin_context['email'])
        sanitized_current_student_email = sanitize_path_part(current_student_email)

        path_1 = f'messages/{sanitized_from_superadmin}-{sanitized_current_student_email}'
        path_2 = f'messages/{sanitized_current_student_email}-{sanitized_from_superadmin}'

        for path in [path_1, path_2]:
            messages_data = db.child(path).get()
            if messages_data and messages_data.each():
                for msg in messages_data.each():
                    message_data = msg.val()
                    decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                    messages.append({
                        'from': message_data['from'],
                        'message': decrypted_message,
                        'timestamp': message_data['timestamp']
                    })

        # Sort messages by timestamp
        messages.sort(key=lambda msg: datetime.strptime(msg['timestamp'], '%B %d, %Y %I:%M %p'))

        return JsonResponse({'messages': messages})

    # Handle message sending or deleting
    if request.method == 'POST':
        if 'delete' in request.POST:
            current_student_email = request.POST.get('student_email')
            if not current_student_email:
                return redirect('sao_message')

            sao_delete_conversation(request, current_student_email)
            return redirect(f'{request.path}?student_email={current_student_email}')

        else:
            message = request.POST.get('message')
            from_superadmin = superadmin_context['email']
            to_student = request.POST.get('to_student_email')

            sanitized_from_superadmin = sanitize_path_part(from_superadmin) if from_superadmin else None
            sanitized_to_student = sanitize_path_part(to_student) if to_student else None

            if not sanitized_from_superadmin or not sanitized_to_student:
                return redirect('sao_message')

            encrypted_message = vigenere_encrypt(message, 'DATALINK')
            message_uid = str(uuid4())

            message_data = {
                'from': from_superadmin,
                'to': to_student,
                'message': encrypted_message,
                'timestamp': datetime.now().strftime('%B %d, %Y %I:%M %p')
            }

            message_path = f'messages/{sanitized_from_superadmin}-{sanitized_to_student}/{message_uid}'
            db.child(message_path).set(message_data)

            return redirect(f'{request.path}?student_email={to_student}')

    # Fetch messages for the selected student if email is provided
    if current_student_email:
        sanitized_from_superadmin = sanitize_path_part(superadmin_context['email'])
        sanitized_current_student_email = sanitize_path_part(current_student_email)
        messages_data = db.child(f'messages/{sanitized_from_superadmin}-{sanitized_current_student_email}').get()

        if messages_data and messages_data.each():
            for msg in messages_data.each():
                message_data = msg.val()
                decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                messages.append({
                    'from': message_data['from'],
                    'message': decrypted_message,
                    'timestamp': message_data['timestamp']
                })

    # Sort messages by timestamp
    messages.sort(key=lambda msg: datetime.strptime(msg['timestamp'], '%B %d, %Y %I:%M %p'))

    # Show modal if the number of messages exceeds a limit
    show_modal = len(messages) >= 15

    # Prepare the context for rendering the page
    context = {
        'selected_student': selected_student,
        'student_list': student_list,
        'current_student_email': current_student_email,
        'messages': messages,
        'show_modal': show_modal,  # Flag for showing the modal
        **superadmin_context,  # Include superadmin context
    }

    return render(request, 'message-sao.html', context)






def delete_conversation_by_sao_owner(request, owner_email):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/saohomepage/message_sao_owner/delete_conversation_by_sao_owner/")

    # Fetch SAO context (for logged-in user)
    sao_context = get_sao_context(request)
    if sao_context is None:  # User is not logged in
        return redirect('sao_login')

    # Sanitize paths for secure Firebase key usage
    sanitized_from_sao = sanitize_path_part(sao_context['email'])  # Use the SAO's email
    sanitized_owner_email = sanitize_path_part(owner_email)

    # Construct the message path in Firebase for the SAO's messages
    path_1 = f'messages/{sanitized_from_sao}-{sanitized_owner_email}'
    # path_2 is for the owner's messages to the SAO, which we will NOT delete
    path_2 = f'messages/{sanitized_owner_email}-{sanitized_from_sao}'

    # Check and delete only the SAO's messages (path_1)
    messages_deleted = False
    messages_data = db.child(path_1).get()
    if messages_data.val() is not None:
        db.child(path_1).remove()
        messages_deleted = True
        print(f"SAO's messages deleted successfully from: {path_1}")

    if not messages_deleted:
        print(f"No SAO's messages found for deletion at path: {path_1}")

    # Redirect back to the conversation with the owner
    redirect_url = f"{reverse('message_sao_owner')}?owner_email={owner_email}"
    return redirect(redirect_url)






def message_sao_owner(request):
    # Fetch SAO context (for example, from session or logged-in user)
    sao_context = get_sao_context(request)
    if sao_context is None:  # User is not logged in
        return redirect('sao_login')

    # Fetch owners data from the database
    owners_data = db.child('owners').get()
    owner_list = []

    if owners_data and owners_data.each():
        for item in owners_data.each():
            owner_email_key = item.key()
            owner_info = {
                'firstname': item.val().get('firstname', 'No Firstname'),
                'lastname': item.val().get('lastname', 'No Lastname'),
                'email': item.val().get('email', 'No Email'),
                'activeStatus': item.val().get('active_status', 'offline'),
                'profileImage': item.val().get('profile_picture', 'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4'),
            }

            # Fetch associated boarding house for the owner
            boarding_house_data = db.child('ownersBoardingHouse').child(owner_email_key).get()
            owner_info['boardinghouseName'] = boarding_house_data.val().get('boardinghouseName', 'No Boarding House') if boarding_house_data and boarding_house_data.val() else 'No Boarding House'

            owner_list.append(owner_info)

    # Determine which owner is selected based on the query parameter 'owner_email'
    current_owner_email = request.GET.get('owner_email')
    selected_owner = None
    if current_owner_email:
        selected_owner = next((owner for owner in owner_list if owner['email'] == current_owner_email), None)
    
    messages = []

    # Handle message sending
    if request.method == 'POST':
        if 'delete' in request.POST:  # Handle delete functionality
            current_owner_email = request.POST.get('owner_email')

            # Debugging: Check if current_owner_email is being passed
            print(f"Received owner_email: {current_owner_email}")

            # Ensure owner_email is not None
            if not current_owner_email:
                print("Error: owner_email is None.")
                return redirect('message_sao_owner')

            # Call the delete function
            delete_conversation_by_sao_owner(request, current_owner_email)

            # Redirect back to the conversation page
            return redirect(f'{request.path}?owner_email={current_owner_email}')

        else:  # Handle sending messages to owner
            message = request.POST.get('message')
            from_sao = sao_context['email']  # Get SAO email from the context
            to_owner = request.POST.get('to_owner_email')

            # Sanitize the email parts
            sanitized_from_sao = sanitize_path_part(from_sao) if from_sao else None
            sanitized_to_owner = sanitize_path_part(to_owner) if to_owner else None

            if not sanitized_from_sao or not sanitized_to_owner:
                print(f"Error: Sanitized path parts are None. from_sao: {sanitized_from_sao}, to_owner: {sanitized_to_owner}")
                return redirect('owner_message')

            # Encrypt the message
            encrypted_message = vigenere_encrypt(message, 'DATALINK')
            message_uid = str(uuid4())

            # Save the message to the database
            message_data = {
                'from': from_sao,
                'to': to_owner,
                'message': encrypted_message,
                'timestamp': datetime.now().strftime('%B %d, %Y %I:%M %p')  # Format the date and time
            }

            message_path = f'messages/{sanitized_from_sao}-{sanitized_to_owner}/{message_uid}'
            db.child(message_path).set(message_data)

            # Redirect after sending the message
            return redirect(f'{request.path}?owner_email={to_owner}')
    
    # Fetch messages for the selected owner
    if current_owner_email:
        sanitized_from_sao = sanitize_path_part(sao_context['email'])
        sanitized_current_owner_email = sanitize_path_part(current_owner_email)

        # Fetch messages from both directions
        path_1 = f'messages/{sanitized_from_sao}-{sanitized_current_owner_email}'
        path_2 = f'messages/{sanitized_current_owner_email}-{sanitized_from_sao}'

        # Fetch messages from the two paths
        for path in [path_1, path_2]:
            messages_data = db.child(path).get()
            if messages_data and messages_data.each():
                for msg in messages_data.each():
                    message_data = msg.val()
                    decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                    messages.append({
                        'from': message_data['from'],
                        'message': decrypted_message,
                        'timestamp': message_data['timestamp']
                    })

    # Sort messages by timestamp
    messages.sort(key=lambda msg: datetime.strptime(msg['timestamp'], '%B %d, %Y %I:%M %p'), reverse=False)

    # Check if the modal should be shown
    show_modal = len(messages) >= 15

    # Handle AJAX request
    if request.is_ajax() and request.method == 'GET':
        return JsonResponse({'messages': messages, 'show_modal': show_modal})

    # Show the page as normal (for non-AJAX requests)
    context = {
        'selected_owner': selected_owner,
        'owner_list': owner_list,  # Include owners in the context
        'messages': messages,
        'current_owner_email': current_owner_email,
        **sao_context,  # Include SAO context in the final context
        'show_modal': show_modal,
        'sao_context': sao_context,
    }

    # Render the page with the context
    return render(request, 'message-sao-owners.html', context)






def delete_conversation_by_owner_student(request, student_email):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "owner/ownerhomepage/owner_message_students/delete_conversation_by_owner_student")

    # Fetch owner context
    owner_context = get_owner_context(request)
    if owner_context is None:  # User is not logged in
        return redirect('owner_login')

    # Sanitize paths for secure Firebase key usage
    sanitized_from_owner = sanitize_path_part(owner_context['email'])
    sanitized_student_email = sanitize_path_part(student_email)

    # Construct the message path in Firebase for the owner's messages
    path_1 = f'messages/{sanitized_from_owner}-{sanitized_student_email}'
    # path_2 is for the student's messages to the owner, which we will NOT delete
    path_2 = f'messages/{sanitized_student_email}-{sanitized_from_owner}'

    # Check and delete only the owner's messages (path_1)
    messages_deleted = False
    messages_data = db.child(path_1).get()
    if messages_data.val() is not None:
        db.child(path_1).remove()
        messages_deleted = True
        print(f"Owner's messages deleted successfully from: {path_1}")

    if not messages_deleted:
        print(f"No owner's messages found for deletion at path: {path_1}")

    # Redirect back to the conversation with the student
    return redirect(reverse('owner_message_students') + f'?student_email={student_email}')






def owner_message_students(request): 
    # Fetch owner context
    owner_context = get_owner_context(request)
    if owner_context is None:  # User is not logged in
        return redirect('owner_login')

    # Fetch student data from the database
    students_data = db.child('students').get()
    student_list = []

    if students_data and students_data.each():
        for item in students_data.each():
            student_info = {
                'email': item.val().get('email', 'No Email'),
                'username': item.val().get('username', 'No Username'),
                'student_id': item.val().get('student_id', 'No Student ID'),
                'profile_picture': item.val().get(
                    'profile_picture',
                    'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4'
                ),
                'active_status': item.val().get('active_status', 'offline'),
            }
            student_list.append(student_info)

    # Determine the selected student
    current_student_email = request.GET.get('student_email')
    selected_student = None
    if current_student_email:
        selected_student = next((student for student in student_list if student['email'] == current_student_email), None)

    # Initialize messages for the first page load
    messages = []

    # Fetch messages on initial load (non-AJAX request)
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Fetch messages between owner and selected student
        if current_student_email:
            sanitized_from_owner = sanitize_path_part(owner_context['email'])
            sanitized_current_student_email = sanitize_path_part(current_student_email)

            path_1 = f'messages/{sanitized_from_owner}-{sanitized_current_student_email}'
            path_2 = f'messages/{sanitized_current_student_email}-{sanitized_from_owner}'

            for path in [path_1, path_2]:
                messages_data = db.child(path).get()
                if messages_data and messages_data.each():
                    for msg in messages_data.each():
                        message_data = msg.val()
                        decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                        messages.append({
                            'from': message_data['from'],
                            'message': decrypted_message,
                            'timestamp': message_data['timestamp']
                        })

            # Sort messages by timestamp
            messages.sort(key=lambda msg: datetime.strptime(msg['timestamp'], '%B %d, %Y %I:%M %p'))

    # Handle AJAX request for fetching messages
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        sanitized_from_owner = sanitize_path_part(owner_context['email'])
        sanitized_current_student_email = sanitize_path_part(current_student_email)

        path_1 = f'messages/{sanitized_from_owner}-{sanitized_current_student_email}'
        path_2 = f'messages/{sanitized_current_student_email}-{sanitized_from_owner}'

        for path in [path_1, path_2]:
            messages_data = db.child(path).get()
            if messages_data and messages_data.each():
                for msg in messages_data.each():
                    message_data = msg.val()
                    decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                    messages.append({
                        'from': message_data['from'],
                        'message': decrypted_message,
                        'timestamp': message_data['timestamp']
                    })

        # Sort messages by timestamp
        messages.sort(key=lambda msg: datetime.strptime(msg['timestamp'], '%B %d, %Y %I:%M %p'))

        # Return messages as JSON response for AJAX request
        return JsonResponse({'messages': messages})

    # Handle message sending or deleting
    if request.method == 'POST':
        if 'delete' in request.POST:
            current_student_email = request.POST.get('student_email')
            if not current_student_email:
                return redirect('owner_message_students')

            delete_conversation_by_owner_student(request, current_student_email)
            return redirect(reverse('owner_message_students') + f'?student_email={current_student_email}')

        else:
            message = request.POST.get('message')
            from_owner = owner_context['email']
            to_student = request.POST.get('to_student_email')

            sanitized_from_owner = sanitize_path_part(from_owner) if from_owner else None
            sanitized_to_student = sanitize_path_part(to_student) if to_student else None

            if not sanitized_from_owner or not sanitized_to_student:
                return redirect('owner_message_students')

            encrypted_message = vigenere_encrypt(message, 'DATALINK')
            message_uid = str(uuid4())

            message_data = {
                'from': from_owner,
                'to': to_student,
                'message': encrypted_message,
                'timestamp': datetime.now().strftime('%B %d, %Y %I:%M %p')
            }

            message_path = f'messages/{sanitized_from_owner}-{sanitized_to_student}/{message_uid}'
            db.child(message_path).set(message_data)

            return redirect(f'{request.path}?student_email={to_student}')

    # Determine if modal should be shown (if there are 15 or more messages)
    show_modal = len(messages) >= 15

    # Prepare the context for rendering the page
    context = {
        'selected_student': selected_student,
        'student_list': student_list,
        'current_student_email': current_student_email,
        **owner_context,
        'messages': messages,  # Include messages in context for template
        'show_modal': show_modal,  # Flag for showing the modal
    }

    return render(request, 'owner-message-students.html', context)










def sao_feedback(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/sao_feedback")

    context = get_sao_context(request)

    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')

    # Specific active page for the feedback
    context['active_page'] = 'feedback'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 
    # Fetch feedback from Firebase
    owners_feedback = db.child('usersReport').child('saofeedback').child('owners').get()
    students_feedback = db.child('usersReport').child('saofeedback').child('students').get()

    # Process feedback data
    feedback_list = []
    total_rating = 0
    rating_count = 0

    # Count feedbacks
    total_owners_feedback_count = 0
    total_students_feedback_count = 0

    # Process Owners Feedback
    if owners_feedback.each() is not None:
        total_owners_feedback_count = len(owners_feedback.each())  # Count owners feedback
        for owner in owners_feedback.each():
            owner_data = owner.val()
            rating = owner_data.get('star_rating', 0)
            feedback_list.append({
                'profile_picture': owner_data.get('profile_picture', 'default-profile.png'),
                'name': owner_data.get('name', 'Unknown'),
                'email': owner_data.get('email', ''),
                'rating': rating,
                'role': 'Owner'
            })
            total_rating += rating
            rating_count += 1

    # Process Students Feedback
    if students_feedback.each() is not None:
        total_students_feedback_count = len(students_feedback.each())  # Count students feedback
        for student in students_feedback.each():
            student_data = student.val()
            rating = student_data.get('star_rating', 0)
            feedback_list.append({
                'profile_picture': student_data.get('profile_picture', 'default-profile.png'),
                'name': student_data.get('name', 'Unknown'),
                'email': student_data.get('email', ''),
                'rating': rating,
                'role': 'Student'
            })
            total_rating += rating
            rating_count += 1

    # Calculate average rating
    average_rating = math.floor(total_rating / rating_count) if rating_count > 0 else 0

    # Define feedback descriptions based on average rating
    if average_rating == 1:
        feedback_description = "Needs Significant Improvement"
    elif average_rating == 2:
        feedback_description = "Below Expectations"
    elif average_rating == 3:
        feedback_description = "Satisfactory Performance"
    elif average_rating == 4:
        feedback_description = "Very Good Performance"
    elif average_rating == 5:
        feedback_description = "Exceptional Performance"
    else:
        feedback_description = "No Feedback Available"

    color = 'red' if average_rating <= 2 else 'green' if average_rating >= 3 else '#6b7280'

    # Add feedback list, average rating, feedback description, and color to context
    context['feedback_list'] = feedback_list
    context['average_rating'] = average_rating
    context['feedback_description'] = feedback_description
    context['feedback_color'] = color
    # Fetch all signed-up students and owners from Firebase
    total_students = db.child("students").get().val() or {}
    total_owners = db.child("owners").get().val() or {}

    # Count total signed-up students and owners
    total_students_count = len(total_students)
    total_owners_count = len(total_owners)
    total_users_count = total_students_count + total_owners_count

    # Add feedback list, average rating, feedback description, and total users count to context
    context['feedback_list'] = feedback_list
    context['average_rating'] = average_rating
    context['feedback_description'] = feedback_description
    context['total_users_count'] = total_users_count  # Add total users count

    # Add total feedback counts to context
    context['total_owners_feedback_count'] = total_owners_feedback_count
    context['total_students_feedback_count'] = total_students_feedback_count

    # Example percentages (replace with actual calculation logic if necessary)
    context['owners_feedback_percentage'] = 85  # Example percentage for owners
    context['students_feedback_percentage'] = 90  # Example percentage for students

    # Render the feedback page with the context
    return render(request, 'sao-feedback.html', context)





def sao_settings(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/sao_settings")
    context = get_sao_context(request)

    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # Profile Update Logic
        if form_type == 'profile_update':
            name = request.POST.get('name')
            birthday = request.POST.get('birthday')
            email = context.get('email')

            if not name or not birthday:
                messages.error(request, "Both name and birthday are required.")
                return render(request, 'sao-settings.html', context)
            
             # Validate birthday format and year range
            try:
                birthday = datetime.strptime(birthday, "%Y-%m-%d").date()

                if birthday.year < 1924 or birthday.year > 2015:
                    messages.error(request, "Birthday is not valid. It should be between 1924 and 2015.")
                    return render(request, 'sao-settings.html', context)

            except ValueError:
                messages.error(request, "Invalid birthday format. Please enter a valid date.")
                return render(request, 'sao-settings.html', context)

            try:
                # Locate the current superadmin
                existing_superadmins = db.child("saoaccounts").child("datas").child("superadmin").get().val()
                print(f"Existing superadmins: {existing_superadmins}")  # Debugging output

                if existing_superadmins:
                    # Attempt to find the correct superadmin key based on email or another identifier
                    current_superadmin_key = None
                    for key, data in existing_superadmins.items():
                        if data.get('email') == email:  # Check if the email matches
                            current_superadmin_key = key
                            break
                    
                    if current_superadmin_key is None:
                        messages.error(request, "No matching superadmin found to update.")
                        return render(request, 'sao-settings.html', context)

                    print(f"Updating superadmin key: {current_superadmin_key}")  # Debugging output

                    # Update the superadmin data
                    updated_data = {
                        "name": name,
                         "birthday": str(birthday)  
                    }

                    # Update the current superadmin's information
                    db.child("saoaccounts").child("datas").child("superadmin").child(current_superadmin_key).update(updated_data)

                    # Confirm the update
                    updated_superadmin = db.child("saoaccounts").child("datas").child("superadmin").child(current_superadmin_key).get().val()
                    print(f"Updated superadmin data: {updated_superadmin}")  # Debugging output

                    context.update(updated_superadmin)
                    messages.success(request, "Profile updated successfully!")
                else:
                    messages.error(request, "No superadmin found to update.")

            except Exception as e:
                print(f"Error during profile update: {str(e)}")  # More detailed error logging
                messages.error(request, f"Error: {str(e)}")

        # Password Update Logic (remains unchanged)
        elif form_type == 'password_update':
            current_password = request.POST.get('currentPassword')
            new_password = request.POST.get('newPassword')
            confirm_password = request.POST.get('confirmPassword')
            email = context.get('email')

            if not current_password or not new_password or not confirm_password:
                messages.error(request, "All password fields are required.")
                return render(request, 'sao-settings.html', context)

            if new_password != confirm_password:
                messages.error(request, "New password and confirm password do not match.")
                return render(request, 'sao-settings.html', context)

            try:
                # Re-authenticate the user
                user = auth_instance.sign_in_with_email_and_password(email, current_password)
                id_token = user['idToken']

                # Use Firebase REST API to update the password
                firebase_api_key = "AIzaSyAfCuib-Q7FmAlr9oj9CIwBONeMkWnpdgU"  # Replace with your actual Firebase API key
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={firebase_api_key}"

                data = {
                    'idToken': id_token,
                    'password': new_password,
                    'returnSecureToken': True
                }

                # Make the API request to update the password
                response = requests.post(url, json=data)
                response_data = response.json()

                if response.status_code == 200:
                    messages.success(request, "Password updated successfully!")
                else:
                    error_message = response_data.get('error', {}).get('message', 'An error occurred')
                    messages.error(request, f"Error: {error_message}")

            except Exception as e:
                if 'INVALID_LOGIN_CREDENTIALS' in str(e):
                    messages.error(request, "Current password does not match our records.")
                else:
                    print(f"Error during password update: {str(e)}")
                    messages.error(request, f"Error: {str(e)}")

    context['active_page'] = 'settings'
    summary_counts = get_summary_counts()
    context.update({ 
        'summary_counts': get_summary_counts,
    }) 
    return render(request, 'sao-settings.html', context)








def pp(request, user_id):
    try:
        # Fetch location from Firebase for the specified user
        location = db.child("locations").child(user_id).get().val()
        if not location:
            return HttpResponse("No location found for this user.", status=404)

        context = {
            "latitude": location.get('latitude'),
            "longitude": location.get('longitude'),
            "api_key": "AIzaSyAwAEWzPd9pu47zsit7JipV38Cu3X2tUSA"
        }
        return render(request, "1111.html", context)
    except Exception as e:
        return HttpResponse(f"Error: {e}", status=500)



def view_students(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "sao/saohomepage/view_students")
    context = get_sao_context(request)
    # Get the SAO context (user info, etc.) 

    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Specific active page for the dashboard
    context['active_page'] = 'dashboard'

    if request.method == "POST":
        # Check if the request is to disable an account
        if 'disable_account' in request.POST:
            email = request.POST.get('email')
            disable_reason = request.POST.get('disableReason')
            
            # Ensure we have an email and a reason provided
            if email and disable_reason:
                # Use the existing email key for the student
                email_key = email.replace('.', '_').replace('@', '_at_')

                # Update account status to disabled
                db.child("students").child(email_key).update({
                    "accountStatus": "disabled",
                    "disableReason": disable_reason  # Save the reason for disabling
                })

                # Prepare email content
                html_message = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 20px;
                        }}
                        .card {{
                            background-color: #ffffff;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                            max-width: 600px;
                            margin: auto;
                            overflow: hidden;
                            padding: 20px;
                        }}
                        .header {{
                            background-color: #007bff;
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }}
                        .content {{
                            margin: 20px 0;
                            font-size: 16px;
                            line-height: 1.5;
                        }}
                        .footer {{
                            text-align: center;
                            margin-top: 20px;
                            font-size: 14px;
                            color: #555;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            margin: 10px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <div class="header">
                            <h2>Account Disabled Notification</h2>
                        </div>
                        <center>
                            <img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo">
                        </center>
                        <div class="content">
                            <p>Hello,</p>
                            <p>Your account has been disabled for the following reason:</p>
                            <p><strong>{disable_reason}</strong></p>
                            <p>If you believe this action was taken in error, please contact support for further assistance. To raise your concern please click the link below.</p>
                            <a href="https://abadddy.pythonanywhere.com/student/student_login/student_report_problem">Raise your concern</a>
                        </div>
                        <div class="footer">
                            <p>Thank you for your understanding!</p>
                            <p>The Datalink Team</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send email notification to the student
                send_mail(
                    'Your Account Has Been Disabled',
                    'Your account has been disabled. Please check your email for more details.',
                    'from@example.com',  # Change to your from email
                    [email],  # Ensure this is the student's email
                    html_message=html_message,
                    fail_silently=False,
                )

                messages.success(request, 'Student account has been disabled successfully, and notification email sent.')
            else:
                messages.error(request, 'Email and reason are required for disabling the account.')
        
        elif 'delete_account' in request.POST:
            email = request.POST.get('email')
            print(f'Received email for deletion: {email}')  # Debug print

            # Ensure the email is provided
            if email:
                email_key = email.replace('.', '_').replace('@', '_at_')

                # Update account status to removed and role to removed
                db.child("students").child(email_key).update({
                    "accountStatus": "removed",
                    "role": "removed"  # Change the role to removed
                })

                # Prepare HTML content for the deletion notification email
                html_message = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 20px;
                        }}
                        .card {{
                            background-color: #ffffff;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                            max-width: 600px;
                            margin: auto;
                            overflow: hidden;
                            padding: 20px;
                        }}
                        .header {{
                            background-color: #ff4b5c;
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }}
                        .content {{
                            margin: 20px 0;
                            font-size: 16px;
                            line-height: 1.5;
                        }}
                        .footer {{
                            text-align: center;
                            margin-top: 20px;
                            font-size: 14px;
                            color: #555;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            margin: 10px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <div class="header">
                            <h2>Account Removal Notification</h2>
                        </div>
                        <center>
                            <img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo">
                        </center>
                        <div class="content">
                            <p>Hello,</p>
                            <p>We regret to inform you that your account has been removed from our system.</p>
                            <p>If you believe this was done in error or if you have any questions, please contact our support team for assistance.</p>
                            <p>Thank you for your understanding. To raise your concern please report it by clicking the link below.</p>
                            <a href="https://abadddy.pythonanywhere.com/student/student_login/student_report_problem">Raise your concern</a>
                        </div>
                        <div class="footer"> 
                            <p>Best regards,<br> The Datalink Team.</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send email notification to the student
                send_mail(
                    'Your Account Has Been Removed',
                    'Your account has been removed from our system.',
                    'from@example.com',  # Change to your "from" email
                    [email],  # Ensure this is the student's email
                    html_message=html_message,
                    fail_silently=False,
                )

                messages.success(request, 'Student account has been removed successfully, and notification email sent.')
            else:
                messages.error(request, 'Email is required for removing the account.')


        else:
            # Handle other form submissions (like updating student info)
            student_id = request.POST.get('student_id')
            username = request.POST.get('username') 
            address = request.POST.get('address')
            gender = request.POST.get('gender')
            course = request.POST.get('course')
            birthday = request.POST.get('birthday')

            # Ensure we have an email provided
            email = request.POST.get('email')
            if email:
                email_key = email.replace('.', '_').replace('@', '_at_')

                # Data to update
                updated_data = {
                    "student_id": student_id,
                    "username": username, 
                    "email": email,
                    "address": address,
                    "gender": gender,
                    "course": course,
                    "birthday": birthday,
                }

                # Update the Firebase Realtime Database
                db.child("students").child(email_key).update(updated_data)

                # Prepare HTML email content for account update
                html_message = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 20px;
                        }}
                        .card {{
                            background-color: #ffffff;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                            max-width: 600px;
                            margin: auto;
                            overflow: hidden;
                            padding: 20px;
                        }}
                        .header {{
                            background-color: #007bff;
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }}
                        .content {{
                            margin: 20px 0;
                            font-size: 16px;
                            line-height: 1.5;
                        }}
                        .footer {{
                            text-align: center;
                            margin-top: 20px;
                            font-size: 14px;
                            color: #555;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            margin: 10px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <div class="header">
                            <h2>Account Update Notification</h2>
                        </div>
                        <center>
                            <img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo">
                        </center>
                        <div class="content">
                            <p>Hello {username},</p>
                            <p>Your account details have been updated by the superadmin.</p>
                            <h3>Updated Information:</h3>
                            <ul>
                                <li><strong>Student ID:</strong> {student_id}</li>
                                <li><strong>Username:</strong> {username}</li> 
                                <li><strong>Email:</strong> {email}</li>
                                <li><strong>Address:</strong> {address}</li>
                                <li><strong>Gender:</strong> {gender}</li>
                                <li><strong>Course:</strong> {course}</li>
                                <li><strong>Birthday:</strong> {birthday}</li>
                            </ul>
                        </div>
                        <a href="https://abadddy.pythonanywhere.com/student/studentsettings/">Check changes in your profile</a>
                        <div class="footer">
                            <p>Thank you for using our service!</p>
                            <p>The Datalink Team</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send email notification to the student
                send_mail(
                    'Your Account Has Been Updated',
                    'Your account details have been updated by the superadmin.',
                    'from@example.com',  # Change to your from email
                    [email],  # Ensure this is the student's email
                    html_message=html_message,
                    fail_silently=False,
                )

                messages.success(request, 'Student information updated successfully and notification email sent.')
            else:
                messages.error(request, 'Email is required for updating student information.')
        
         

        return redirect('view_students')  # Redirect to the view_students page after update

    # Fetch all students from the Firebase 'students' node
    students_data = db.child("students").get()

    # List to store approved students
    approved_students = []

    # Loop through students and filter based on accountStatus
    if students_data.each() is not None:
        for student in students_data.each():
            student_data = student.val()
            # Check if accountStatus is 'approved'
            if student_data.get('accountStatus') == 'approved':
                approved_students.append(student_data)

    # Add approved students to the context
    context['approved_students'] = approved_students
    total_pending_accounts = count_pending_accounts()
    summary_counts = get_summary_counts()
    context.update({
        'total_pending_accounts': total_pending_accounts,
        'summary_counts': get_summary_counts, 
    }) 
    # Pass both the approved students and the context to the template
    return render(request, 'approved-students.html', context)


def view_owners(request):
    context = get_sao_context(request)  # Retrieve the context based on your implementation of get_sao_context

    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing
    context['active_page'] = 'dashboard'
    total_pending_accounts = count_pending_accounts()
    summary_counts = get_summary_counts()
    context.update({
        'total_pending_accounts': total_pending_accounts,
        'summary_counts': get_summary_counts,
    }) 

    # Retrieve owner email from session (used for logging in, not for fetching data)
    owner_email = request.session.get('email')
    if not owner_email:
        messages.error(request, 'Owner email not found in session. Please log in again.')
        return redirect('sao_login')

    # Initialize owners_data to be passed to the template
    owners_data = []
    students_data = []

    # Handle form submission for updating an owner's profile or disabling an account
    if request.method == 'POST':
        if 'delete_account' in request.POST:
            # Handle account removal action
            email = request.POST.get('email')
            email_key = email.replace('.', '_').replace('@', '_at_')  # Format email to create Firebase key

            try:
                # Update accountStatus and boardinghouseStatus to 'removed'
                db.child("owners").child(email_key).update({
                    'accountStatus': 'removed',
                    'role': 'removed'  # Update the role to "removed"
                })
                db.child("ownersBoardingHouse").child(email_key).update({'boardinghouseStatus': 'removed'})
                
                messages.success(request, 'Owner account and boardinghouse status marked as removed.')
            except Exception as e:
                messages.error(request, f"Error removing owner account: {str(e)}")

        elif 'disable_account' in request.POST:
            # Handle disable account action
            email = request.POST.get('email')
            disable_reason = request.POST.get('disableReason')
            
            # Format the email to create the Firebase key
            email_key = email.replace('.', '_').replace('@', '_at_')
            
            try:
                # Update accountStatus and disabledReason in "owners"
                db.child("owners").child(email_key).update({
                    'accountStatus': 'disabled',
                    'disabledReason': disable_reason
                })

                # Update boardinghouseStatus in "ownersBoardingHouse"
                db.child("ownersBoardingHouse").child(email_key).update({
                    'boardinghouseStatus': 'disabled'
                })
                
                messages.success(request, 'Owner account and boardinghouse status disabled successfully.')
            except Exception as e:
                messages.error(request, f"Error disabling owner account: {str(e)}")
        
        else:
            # Update owner profile information
            email = request.POST.get('email')
            firstname = request.POST.get('firstname')
            middlename = request.POST.get('middlename')
            lastname = request.POST.get('lastname')
            phone_number = request.POST.get('phone_number')
            address = request.POST.get('address')
            gender = request.POST.get('gender')
            birthday = request.POST.get('birthday')

            # Format the email to create the Firebase key
            email_key = email.replace('.', '_').replace('@', '_at_')
            try:
                # Update the owner's information in Firebase 
                updated_data = {
                    'firstname': firstname,
                    'middlename': middlename,
                    'lastname': lastname,
                    'phone_number': phone_number,
                    'address': address,
                    'gender': gender,
                    'birthday': birthday,
                }
                # Update the data in the Firebase database
                db.child("owners").child(email_key).update(updated_data)
                messages.success(request, 'Owner data updated successfully.')
            except Exception as e:
                messages.error(request, f"Error updating owner data: {str(e)}")

    # Fetch data for all owners
    try:
        # Fetch all owners and their boarding house names
        all_owners = db.child("ownersBoardingHouse").get().val()
        owners_boardinghouses = {}
        if all_owners:
            for owner_key, owner_data in all_owners.items():
                if owner_data.get('boardinghouseName') and owner_data.get('boardinghouseStatus') == "approved":
                    owners_boardinghouses[owner_key] = owner_data.get('boardinghouseName')

        # Fetch all students
        all_students = db.child("students").get().val()
        students_data = []
        if all_students:
            for student_key, student_data in all_students.items():
                # Match students to any approved boarding house
                student_bh_name = student_data.get('boardinghouseName')
                if student_bh_name in owners_boardinghouses.values():
                    students_data.append({
                        'name': f"{student_data.get('firstname')} {student_data.get('lastname')}",
                        'username': student_data.get('username'),
                        'student_id': student_data.get('student_id'),
                        'schedule_date': student_data.get('schedule_date'),
                        'roomName': student_data.get('roomName'),
                        'profile_picture': student_data.get('profile_picture'),
                        'boardinghouseName': student_bh_name,
                    })







        # Fetch the whole owners node (list of all owners)
        all_owners_data = db.child("owners").get().val()
        if all_owners_data:
            for owner_key, owner_data in all_owners_data.items():
                if owner_data.get('accountStatus') == "approved":  # Only show approved owners
                    owner = {
                        'firstname': owner_data.get('firstname'),
                        'middlename': owner_data.get('middlename'),
                        'lastname': owner_data.get('lastname'),
                        'phone_number': owner_data.get('phone_number'),
                        'email': owner_data.get('email'),
                        'active_status': owner_data.get('active_status'),
                        'daysLogin': owner_data.get('daysLogin'),
                        'timeLoggedOut': owner_data.get('timeLoggedOut'),
                        'profile_picture': owner_data.get('profile_picture'),
                        'accountStatus': owner_data.get('accountStatus'),
                        'address': owner_data.get('address'),
                        'gender': owner_data.get('gender'),
                        'birthday': owner_data.get('birthday'),
                        'signup_time': owner_data.get('signup_time')
                    }

                    # Fetch the boarding house data for each owner
                    email_key = owner['email'].replace('.', '_').replace('@', '_at_')  # Format email for each owner
                    boardinghouse_data = db.child("ownersBoardingHouse").child(email_key).get().val()
                    if boardinghouse_data:
                        owner['boardinghouseName'] = boardinghouse_data.get('boardinghouseName')
                        owner['boardinghouseStatus'] = boardinghouse_data.get('boardinghouseStatus')
                    else:
                        owner['boardinghouseName'] = 'No boarding house data'
                        owner['boardinghouseStatus'] = 'Not available'

                    owners_data.append(owner)
        else:
            messages.warning(request, 'No owners data found in the database.')
    except Exception as e:
        messages.error(request, f"Error fetching owner data: {str(e)}")

    # Add owners data to context
    context.update({
        'owners': owners_data,  # List of owners data
        'students': students_data,
        'owners_boardinghouses': owners_boardinghouses,
    })

    # Render the page with context
    return render(request, 'approved-owners.html', context)






def view_owners_boarding_house(request):
    if request.method == 'POST':
        owner_email = request.POST.get('owner_email')
        print(f"Owner email fetched: {owner_email}")  # Debugging step

        if not owner_email:
            messages.error(request, 'No email provided in the form submission.')
            # Just render the page with the error message, no redirect
            return render(request, 'approved-owners-viewBH.html')

        try:
            # Process email to get email_key
            email_key = owner_email.replace('.', '_').replace('@', '_at_')

            # Fetch boarding house data from 'ownersBoardingHouse'
            boarding_house_info = db.child('ownersBoardingHouse').child(email_key).get().val()
            print(f"Boarding house info: {boarding_house_info}")  # Debugging step

            # If no boarding house info found, add an error message and render the page
            if not boarding_house_info:
                messages.error(request, 'No boarding house data found for this owner.')
                return render(request, 'approved-owners-viewBH.html')

            # Extract required fields from the boarding house info
            fullname = boarding_house_info.get('name', None)
            boardinghouse_name = boarding_house_info.get('boardinghouseName', None)
            about_us = boarding_house_info.get('aboutUs', None)
            cover_photo_url = boarding_house_info.get('coverPhoto', None)
            profile_picture = boarding_house_info.get('profile_picture', None)
            wifi_available = boarding_house_info.get('wifiAvailable', None)
            free_electric_bill = boarding_house_info.get('freeElectricBill', None)
            free_water_bill = boarding_house_info.get('freeWaterBill', None)
            type_of_rental = boarding_house_info.get('typeOfRental', None)
            parking_space = boarding_house_info.get('parkingSpace', None)
            securityFeatures_keys = boarding_house_info.get('securityFeatures_keys', None)
            securityFeatures_curfew = boarding_house_info.get('securityFeatures_curfew', None)
            securityFeatures_cctv = boarding_house_info.get('securityFeatures_cctv', None)
            boardinghouse_status = boarding_house_info.get('boardinghouseStatus', None)
            email = boarding_house_info.get('email', None)

            # Initialize empty lists for amenities, documents, and rooms (if not already present)
            amenities = boarding_house_info.get('amenities', [])
            documents = boarding_house_info.get('documents', [])
            rooms = boarding_house_info.get('rooms', [])

            # Fetch ratings from the database
            ratings = boarding_house_info.get('ratings', {})
            average_rating = 0  # Default rating if no ratings exist
            total_reviews = 0  # Default if no ratings exist

            if ratings:
                # Calculate total rating
                total_rating = sum(rating['rating'] for rating in ratings.values())
                # Calculate average rating
                average_rating = total_rating / len(ratings) if len(ratings) > 0 else 0
                # Calculate the number of users who gave ratings
                total_reviews = len(ratings)
                # Round the average rating
                average_rating = round(average_rating)

            # Add the calculated average rating and total reviews to the owner_data
            owner_data = {
                'name': fullname,
                'boardinghouseName': boardinghouse_name,
                'aboutUs': about_us,
                'coverPhoto': cover_photo_url,
                'profile_picture': profile_picture,
                'amenities': amenities,
                'documents': documents,
                'rooms': rooms,
                'wifiAvailable': wifi_available,
                'freeElectricBill': free_electric_bill,
                'freeWaterBill': free_water_bill,
                'typeOfRental': type_of_rental,
                'parkingSpace': parking_space,
                'securityFeatures_keys': securityFeatures_keys,
                'securityFeatures_curfew': securityFeatures_curfew,
                'securityFeatures_cctv': securityFeatures_cctv,
                'boardinghouseStatus': boardinghouse_status,
                'email': email,
                'averageRating': average_rating,  # Include the average rating
                'totalReviews': total_reviews,  # Include total reviews count
            }

            # Prepare the data to pass to the template
            context = {
                'boardinghouse_data': owner_data,
                'owner': boarding_house_info,
                'star_range': range(1, 6), 
            }

            # Render the profile page with the fetched data
            return render(request, 'approved-owners-viewBH.html', context)

        except Exception as e:
            # In case of error, add a generic error message
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'approved-owners-viewBH.html')  # Render the page with the error

    else:
        # Handle GET request or any invalid method
        messages.error(request, 'Invalid request')
        return render(request, 'approved-owners-viewBH.html')  # Render the page with the error






 
def pendingreq(request): 
    context = get_sao_context(request)
    
    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')  # Redirect to login page if email is missing

    # Specific active page for the pending requests
    context['active_page'] = 'dashboard'
    total_pending_accounts = count_pending_accounts()
    summary_counts = get_summary_counts()
    context.update({
        'total_pending_accounts': total_pending_accounts,
        'summary_counts': get_summary_counts,
    }) 
    try:
        # Approve student functionality: check if there's an email in the POST request to approve
        if request.method == "POST":
            # Approve student
            if 'approve_student_email' in request.POST:
                approve_student_email = request.POST.get('approve_student_email')
                
                # Convert email to the email_key format (replacing '.' and '@')
                email_key = approve_student_email.replace('.', '_').replace('@', '_at_')
                
                # Update the student's accountStatus to approved in Firebase
                db.child("students").child(email_key).update({"accountStatus": "approved"})
                messages.success(request, f'Student with email {approve_student_email} has been approved.')

                # HTML message for approval notification
                html_message = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 20px;
                        }}
                        .card {{
                            background-color: #ffffff;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                            max-width: 600px;
                            margin: auto;
                            overflow: hidden;
                            padding: 20px;
                        }}
                        .header {{
                            background-color: #007bff;
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }}
                        .content {{
                            margin: 20px 0;
                            font-size: 16px;
                            line-height: 1.5;
                        }}
                        .footer {{
                            text-align: center;
                            margin-top: 20px;
                            font-size: 14px;
                            color: #555;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            margin: 10px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <div class="header">
                            <h2>Account Approval Notification</h2>
                        </div>
                        <center><img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo"></center>
                        <div class="content">
                            <p>Hello Student,</p>
                            <p>Your account has now been approved. You can now apply for boarding houses. <a href="https://abadddy.pythonanywhere.com/student/student_login/">Take me to Login page</a></p>
                        </div>
                        <div class="footer">
                            <p>Thank you for using our service!</p>
                            <p>The Datalink Team</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send email notification for approval
                send_mail(
                    subject='Your Account Has Been Approved',
                    message='',
                    html_message=html_message,
                    from_email='your_email@example.com',  # Replace with your email
                    recipient_list=[approve_student_email],
                    fail_silently=False,
                )

            # Reject student
            elif 'reject_student_email' in request.POST:
                reject_student_email = request.POST.get('reject_student_email')
                reject_reason = request.POST.get('reject_reason')  # Get the selected reject reason
                
                # Convert email to the email_key format (replacing '.' and '@')
                email_key = reject_student_email.replace('.', '_').replace('@', '_at_')
                
                # Update the student's accountStatus to rejected in Firebase
                db.child("students").child(email_key).update({"accountStatus": "rejected"})
                messages.success(request, f'Student with email {reject_student_email} has been rejected.')

                # HTML message for rejection notification
                rejection_html_message = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 20px;
                        }}
                        .card {{
                            background-color: #ffffff;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                            max-width: 600px;
                            margin: auto;
                            overflow: hidden;
                            padding: 20px;
                        }}
                        .header {{
                            background-color: #dc3545;  /* Red background for rejection */
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }}
                        .content {{
                            margin: 20px 0;
                            font-size: 16px;
                            line-height: 1.5;
                        }}
                        .footer {{
                            text-align: center;
                            margin-top: 20px;
                            font-size: 14px;
                            color: #555;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            margin: 10px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <div class="header">
                            <h2>Account Rejection Notification</h2>
                        </div>
                        <center><img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo"></center>
                        <div class="content">
                            <p>Hello Student,</p>
                            <p>Sorry to inform you, but your account has been rejected due to the following reason:</p>
                            <p><strong>{reject_reason}</strong></p>
                            <p>Please contact support for further assistance. To raise your concerns, go to our Login page and below click report a problem. Or open this link below.</p>
                            <a href="https://abadddy.pythonanywhere.com/student/student_login/student_report_problem">Raise your concern</a>
                        </div>
                        <div class="footer">
                            <p>Thank you for your understanding!</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send email notification for rejection
                send_mail(
                    subject='Your Account Has Been Rejected',
                    message='',
                    html_message=rejection_html_message,
                    from_email='your_email@example.com',  # Replace with your email
                    recipient_list=[reject_student_email],
                    fail_silently=False,
                )

        # Fetch all students from the "students" node
        students_data = db.child("students").get()

        # Fetch all students from the "studentdatabase/datas" node
        registered_students_data = db.child("studentdatabase").child("datas").get().val()

        # Parse the students data into a list of dictionaries
        students = []
        if students_data.each():
            for student in students_data.each():
                student_info = student.val()
                student_info['id'] = student.key()  # Get the unique key (email as id in your case)
                
                # Check if the student exists and matches in "studentdatabase/datas"
                student_id = student_info.get('student_id')
                student_course = student_info.get('course')
                student_birthday = student_info.get('birthday')

                # Retrieve corresponding data from registered students
                if registered_students_data and student_id in registered_students_data:
                    registered_student = registered_students_data[student_id]
                    
                    # Match student_id, course, and birthday
                    student_info['is_matched'] = (registered_student.get('course') == student_course and
                                                   registered_student.get('birthday') == student_birthday)
                else:
                    student_info['is_matched'] = False  # Mark as unmatched

                # Fetch the profile picture if it exists, or set a default picture
                profile_picture_url = student_info.get('profile_picture', 'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4')
                student_info['profile_picture'] = profile_picture_url

                students.append(student_info)
        
        # Pass the list of students to the template, along with the context
        owners = fetch_owners()
        context['students'] = students  # Add the students to the context
        context['owners'] = owners 
        return render(request, 'pendingrequest.html', context)  # Render with the complete context

    except Exception as e:
        messages.error(request, f"Error fetching students: {str(e)}")
        return render(request, 'pendingrequest.html', context)  # Render with context even in case of an error


def fetch_owners():
    try:
        # Fetch all owners from the "owners" node in Firebase
        owners_data = db.child("owners").get()
        owners = []
        
        if owners_data.each():
            for owner in owners_data.each():
                owner_info = owner.val()
                owner_info['id'] = owner.key()  # Get the unique key (email as id in your case)

                # Fetch the owner's profile picture if it exists, or set a default picture
                profile_picture_url = owner_info.get('profile_picture', 'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4')
                owner_info['profile_picture'] = profile_picture_url

                # Generate email_key by replacing '.' with '_' and '@' with '_at_' for 'ownersBoardingHouse' data retrieval
                email = owner_info.get('email', '')
                email_key = email.replace('.', '_').replace('@', '_at_')
                
                # Fetch additional saved owner data from 'ownersBoardingHouse'
                saved_owner_data = db.child('ownersBoardingHouse').child(email_key).get().val()
                
                # Merge saved_owner_data into owner_info if it exists
                if saved_owner_data:
                    owner_info.update(saved_owner_data)

                owners.append(owner_info)

        return owners

    except Exception as e:
        print(f"Error fetching owners: {str(e)}")
        return []


def boardinghouseAction(request):
    if request.method == 'POST':
        # Identify the owner's email from the form submission
        email = request.POST.get('owner_email', '')
        if not email:
            messages.error(request, 'Email is required.')
            return redirect('pendingreq')  # Redirecting to pending requests

        # Generate the email_key for Firebase
        email_key = email.replace('.', '_').replace('@', '_at_')  

        try:
            if 'approve' in request.POST:
                # Handle the approval action
                db.child('owners').child(email_key).update({'accountStatus': 'approved'})
                db.child('ownersBoardingHouse').child(email_key).update({'boardinghouseStatus': 'approved'}) 
                
                # Fetch the boarding house details
                boardinghouse_data = db.child('ownersBoardingHouse').child(email_key).get().val()
                boardinghouse_name = boardinghouse_data.get('boardinghouseName', 'Unknown Boarding House')

                # Fetch owner details
                owner_data = db.child('owners').child(email_key).get().val()
                owner_fullname = f"{owner_data.get('firstname', '')} {owner_data.get('middlename', '')} {owner_data.get('lastname', '')}".strip()
                owner_email = owner_data.get('email', 'Not Provided')
                owner_address = owner_data.get('address', 'Not Provided')
                owner_phone = owner_data.get('phone_number', 'Not Provided')

                # Prepare the HTML message for approval notification
                html_message = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <link href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" rel="stylesheet">
                    <style>
                        body {{
                            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
                            background-color: #e5e7eb;
                            margin: 0;
                            padding: 40px 20px;
                            color: #1f2937;
                            line-height: 1.6;
                        }}

                        .envelope {{
                            max-width: 600px;
                            margin: 0 auto;
                            background: linear-gradient(145deg, #ffffff 0%, #f3f4f6 100%);
                            border-radius: 16px;
                            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1),
                                        0 8px 10px -6px rgba(0, 0, 0, 0.1);
                            overflow: hidden;
                            position: relative;
                        }}

                        .envelope::before {{
                            content: '';
                            position: absolute;
                            top: 0;
                            left: 0;
                            right: 0;
                            height: 6px;
                            background: linear-gradient(90deg, #1e40af, #3b82f6);
                        }}

                        .card {{
                            background-color: #ffffff;
                            margin: 20px;
                            border-radius: 12px;
                            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                            overflow: hidden;
                        }}

                        .header {{
                            background: linear-gradient(135deg, #1e40af, #3b82f6);
                            color: white;
                            padding: 2rem;
                            text-align: center;
                            position: relative;
                        }}

                        .header::after {{
                            content: '';
                            position: absolute;
                            bottom: -20px;
                            left: 50%;
                            transform: translateX(-50%);
                            border-top: 20px solid #3b82f6;
                            border-left: 20px solid transparent;
                            border-right: 20px solid transparent;
                        }}

                        .header h2 {{
                            margin: 0;
                            font-size: 1.75rem;
                            font-weight: 700;
                            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        }}

                        .logo-container {{
                            text-align: center;
                            padding: 2rem;
                            margin-top: 1rem;
                            position: relative;
                        }}

                        .logo-container img {{
                            width: 140px;
                            height: auto;
                            border-radius: 12px;
                            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                            transition: transform 0.3s ease;
                        }}

                        .logo-container img:hover {{
                            transform: scale(1.05);
                        }}

                        .content {{
                            padding: 2rem;
                        }}

                        .approval-badge {{
                            background: linear-gradient(135deg, #059669, #10b981);
                            color: white;
                            font-size: 1.5rem;
                            font-weight: 700;
                            padding: 0.75rem 2rem;
                            border-radius: 999px;
                            display: inline-block;
                            margin: 1rem 0;
                            box-shadow: 0 4px 6px -1px rgba(5, 150, 105, 0.3);
                            animation: fadeInDown 0.8s ease-out;
                            text-transform: uppercase;
                            letter-spacing: 0.05em;
                        }}

                        .details-section {{
                            background-color: #f8fafc;
                            border-radius: 12px;
                            padding: 1.5rem;
                            margin: 1.5rem 0;
                            border: 1px solid #d1d5db;
                        }}

                        .details-section h3 {{
                            margin: 0 0 1.25rem 0;
                            color: #1e40af;
                            font-size: 1.25rem;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 0.5rem;
                        }}

                        .details-section h3::before {{
                            content: '';
                            display: inline-block;
                            width: 4px;
                            height: 1em;
                            background-color: #1e40af;
                            border-radius: 4px;
                        }}

                        .details-list {{
                            list-style: none;
                            padding: 0;
                            margin: 0;
                        }}

                        .details-list li {{
                            margin-bottom: 1rem;
                            display: flex;
                            align-items: baseline;
                            padding-left: 1rem;
                        }}

                        .details-list strong {{
                            min-width: 140px;
                            color: #4b5563;
                            position: relative;
                        }}

                        .details-list strong::after {{
                            content: ':';
                            position: absolute;
                            right: 1rem;
                        }}

                        .footer {{
                            text-align: center;
                            padding: 2rem;
                            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
                            border-top: 1px solid #d1d5db;
                            font-size: 0.925rem;
                            color: #64748b;
                        }}

                        .message {{
                            background-color: #f0f9ff;
                            border-left: 4px solid #3b82f6;
                            padding: 1rem;
                            margin: 1.5rem 0;
                            border-radius: 0 8px 8px 0;
                        }}

                        @keyframes fadeInDown {{
                            from {{
                                opacity: 0;
                                transform: translateY(-20px);
                            }}
                            to {{
                                opacity: 1;
                                transform: translateY(0);
                            }}
                        }}

                        @media (max-width: 640px) {{
                            body {{
                                padding: 20px 10px;
                            }}

                            .header h2 {{
                                font-size: 1.5rem;
                            }}

                            .details-list li {{
                                flex-direction: column;
                            }}

                            .details-list strong {{
                                margin-bottom: 0.25rem;
                            }}

                            .details-list strong::after {{
                                display: none;
                            }}
                        }}
                    </style>
                </head>
                <body>
                    <div class="envelope animate__animated animate__fadeIn">
                        <div class="card">
                            <div class="header">
                                <h2>Account Approval Notification</h2>
                            </div>
                            <div class="logo-container">
                                <img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo">
                            </div>
                            <div class="content">
                                <center>
                                    <div class="approval-badge">Approved!</div>
                                </center>
                                
                                <div class="message">
                                    <p>Your boarding house with the name <strong>{boardinghouse_name}</strong> has now been approved by the SAO. Students can now apply to your boarding house.</p>
                                </div>
                                
                                <div class="details-section">
                                    <h3>Owner's Profile</h3>
                                    <ul class="details-list">
                                        <li><strong>Email</strong> {owner_email}</li>
                                        <li><strong>Full Name</strong> {owner_fullname}</li>
                                        <li><strong>Address</strong> {owner_address}</li>
                                        <li><strong>Phone</strong> {owner_phone}</li>
                                    </ul>
                                </div>
                                <a href="https://abadddy.pythonanywhere.com/owner/owner_login/">Take me to Login page</a>
                            </div>
                            <div class="footer">
                                <p>Thank you for choosing our service! We look forward to helping you connect with students.</p>
                                <p>The Datalink Team</p> 
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send the email
                send_mail(
                    subject='Your Boarding House Has Been Approved!',
                    message='This is a notification email.',
                    from_email='your_email@example.com',  # Update with your sender email
                    recipient_list=[email],
                    html_message=html_message,
                )

                messages.success(request, 'Boarding house approved successfully!')
                messages.success(request, f'This boarding house "{boardinghouse_name}" is now accredited in CTU AC.')
                return redirect('pendingreq')  # Redirect to pending requests

            elif 'reject_reason' in request.POST:
                # Handle the rejection action with reason
                reject_reason = request.POST.get('reject_reason', '')
                db.child('owners').child(email_key).update({
                    'accountStatus': 'rejected',
                    'rejectionReason': reject_reason
                })
                db.child('ownersBoardingHouse').child(email_key).update({'boardinghouseStatus': 'rejected'})

                # Fetch owner details for the rejection email
                owner_data = db.child('owners').child(email_key).get().val()
                owner_fullname = f"{owner_data.get('firstname', '')} {owner_data.get('middlename', '')} {owner_data.get('lastname', '')}".strip()
                boardinghouse_data = db.child('ownersBoardingHouse').child(email_key).get().val()
                boardinghouse_name = boardinghouse_data.get('boardinghouseName', 'Unknown Boarding House')
                owner_email = owner_data.get('email', 'Not Provided')
                owner_address = owner_data.get('address', 'Not Provided')
                owner_phone = owner_data.get('phone_number', 'Not Provided')
                # Prepare the rejection HTML message
                rejection_html_message = f""" 
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <link href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" rel="stylesheet">
                    <style>
                        body {{
                            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
                            background-color: #fef2f2;
                            margin: 0;
                            padding: 40px 20px;
                            color: #1f2937;
                            line-height: 1.6;
                        }}

                        .envelope {{
                            max-width: 600px;
                            margin: 0 auto;
                            background: linear-gradient(145deg, #ffffff 0%, #f8d7da 100%);
                            border-radius: 16px;
                            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1),
                                        0 8px 10px -6px rgba(0, 0, 0, 0.1);
                            overflow: hidden;
                            position: relative;
                        }}

                        .envelope::before {{
                            content: '';
                            position: absolute;
                            top: 0;
                            left: 0;
                            right: 0;
                            height: 6px;
                            background: linear-gradient(90deg, #b91c1c, #ef4444);
                        }}

                        .card {{
                            background-color: #ffffff;
                            margin: 20px;
                            border-radius: 12px;
                            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                            overflow: hidden;
                        }}

                        .header {{
                            background: linear-gradient(135deg, #b91c1c, #ef4444);
                            color: white;
                            padding: 2rem;
                            text-align: center;
                            position: relative;
                        }}

                        .header::after {{
                            content: '';
                            position: absolute;
                            bottom: -20px;
                            left: 50%;
                            transform: translateX(-50%);
                            border-top: 20px solid #ef4444;
                            border-left: 20px solid transparent;
                            border-right: 20px solid transparent;
                        }}

                        .header h2 {{
                            margin: 0;
                            font-size: 1.75rem;
                            font-weight: 700;
                            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        }}

                        .logo-container {{
                            text-align: center;
                            padding: 2rem;
                            margin-top: 1rem;
                            position: relative;
                        }}

                        .logo-container img {{
                            width: 140px;
                            height: auto;
                            border-radius: 12px;
                            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                            transition: transform 0.3s ease;
                        }}

                        .logo-container img:hover {{
                            transform: scale(1.05);
                        }}

                        .content {{
                            padding: 2rem;
                        }}

                        .rejection-badge {{
                            background: linear-gradient(135deg, #dc2626, #f87171);
                            color: white;
                            font-size: 1.5rem;
                            font-weight: 700;
                            padding: 0.75rem 2rem;
                            border-radius: 999px;
                            display: inline-block;
                            margin: 1rem 0;
                            box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.3);
                            animation: fadeInDown 0.8s ease-out;
                            text-transform: uppercase;
                            letter-spacing: 0.05em;
                        }}

                        .details-section {{
                            background-color: #fef2f2;
                            border-radius: 12px;
                            padding: 1.5rem;
                            margin: 1.5rem 0;
                            border: 1px solid #fca5a5;
                        }}

                        .details-section h3 {{
                            margin: 0 0 1.25rem 0;
                            color: #991b1b;
                            font-size: 1.25rem;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                            gap: 0.5rem;
                        }}

                        .details-section h3::before {{
                            content: '';
                            display: inline-block;
                            width: 4px;
                            height: 1em;
                            background-color: #991b1b;
                            border-radius: 4px;
                        }}

                        .details-list {{
                            list-style: none;
                            padding: 0;
                            margin: 0;
                        }}

                        .details-list li {{
                            margin-bottom: 1rem;
                            display: flex;
                            align-items: baseline;
                            padding-left: 1rem;
                        }}

                        .details-list strong {{
                            min-width: 140px;
                            color: #4b5563;
                            position: relative;
                        }}

                        .details-list strong::after {{
                            content: ':';
                            position: absolute;
                            right: 1rem;
                        }}

                        .footer {{
                            text-align: center;
                            padding: 2rem;
                            background: linear-gradient(180deg, #fef2f2 0%, #fde8e8 100%);
                            border-top: 1px solid #fca5a5;
                            font-size: 0.925rem;
                            color: #9ca3af;
                        }}

                        .message {{
                            background-color: #fef2f2;
                            border-left: 4px solid #ef4444;
                            padding: 1rem;
                            margin: 1.5rem 0;
                            border-radius: 0 8px 8px 0;
                        }}

                        @keyframes fadeInDown {{
                            from {{
                                opacity: 0;
                                transform: translateY(-20px);
                            }}
                            to {{
                                opacity: 1;
                                transform: translateY(0);
                            }}
                        }}

                        @media (max-width: 640px) {{
                            body {{
                                padding: 20px 10px;
                            }}

                            .header h2 {{
                                font-size: 1.5rem;
                            }}

                            .details-list li {{
                                flex-direction: column;
                            }}

                            .details-list strong {{
                                margin-bottom: 0.25rem;
                            }}

                            .details-list strong::after {{
                                display: none;
                            }}
                        }}
                    </style>
                </head>
                <body>
                    <div class="envelope animate__animated animate__fadeIn">
                        <div class="card">
                            <div class="header">
                                <h2>Account Rejection Notification</h2>
                            </div>
                            <div class="logo-container">
                                <img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo">
                            </div>
                            <div class="content">
                                <center>
                                    <div class="rejection-badge">Rejected</div>
                                </center>
                                
                                <div class="message">
                                    <p>We regret to inform you that your boarding house, <strong>{boardinghouse_name}</strong>, has not been approved. Please check the guidelines and requirements, and consider reapplying if you meet the necessary criteria.</p>
                                </div>
                                <p>We regret to inform you that your application for the boarding house has been rejected due to the following reason:</p>
                                <blockquote style="background-color: #f0f0f0; padding: 10px; border-left: 4px solid #d9534f;">
                                    {reject_reason}
                                </blockquote>
                                
                                <div class="details-section">
                                    <h3>Owner's Profile</h3>
                                    <ul class="details-list">
                                        <li><strong>Email</strong> {owner_email}</li>
                                        <li><strong>Full Name</strong> {owner_fullname}</li>
                                        <li><strong>Address</strong> {owner_address}</li>
                                        <li><strong>Phone</strong> {owner_phone}</li>
                                    </ul>
                                </div>
                                <p>Thank you for your interest in our service. Please reach out to us if you have any questions by clicking the link below.</p>
                                <a href="https://abadddy.pythonanywhere.com/owner/owner_login/owner_report_problem">Raise your concern</a>
                            </div>
                            <div class="footer">
                                <p>Best regards, </p>
                                <p>The Datalink Team</p> 
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send the rejection email
                send_mail(
                    subject='Your Boarding House Application Has Been Rejected',
                    message='This is a notification email.',
                    from_email='your_email@example.com',  # Replace with your sender email
                    recipient_list=[email],
                    html_message=rejection_html_message,
                )

                messages.success(request, 'Boarding house rejected successfully, and notification email sent!')
                return redirect('pendingreq')  # Redirect to pending requests

        except Exception as e:
            print(f"Error updating owner status: {str(e)}")
            messages.error(request, 'Failed to update owner status.')
            return redirect('pendingreq')  # Redirecting to pending requests

    # Fetch the owner's boarding house data for rendering if the request is not POST
    email = request.POST.get('owner_email', '')
    if not email:
        messages.error(request, 'Email is required to fetch data.')
        return redirect('pendingreq')  # Redirecting to pending requests

    email_key = email.replace('.', '_').replace('@', '_at_')  # Generate the email key for fetching data

    try:
        # Fetch the owner's boarding house data
        owner_data = db.child('ownersBoardingHouse').child(email_key).get().val()
        
        # If owner data is None, initialize it as an empty dictionary
        if owner_data is None:
            owner_data = {}
        else:
            # Retrieve the rooms data, defaulting to an empty list if not present
            rooms = owner_data.get('rooms', [])
            owner_data['rooms'] = rooms

        # Render the template with owner data and rooms
        return render(request, 'boardinghouseAction.html', {'owner_data': owner_data})
    except Exception as e:
        print(f"Error fetching boarding house data: {str(e)}")
        messages.error(request, 'Error fetching boarding house data.')
        return redirect('pendingreq')  # Redirecting to pending requests



def generatingReports(request):
    context = get_sao_context(request)
    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')

    try:
        # Fetch boarding house data
        boarding_houses = db.child('ownersBoardingHouse').get().val() or {}
        students = db.child('students').get().val() or {}

        reports = []

        for owner_email, data in boarding_houses.items():
            boardinghouse_name = data.get('boardinghouseName', 'N/A')
            boardinghouse_status = data.get('boardinghouseStatus', 'N/A')
            owner_name = data.get('name', 'N/A')
            owner_email = data.get('email', 'N/A')
            type_of_rental = data.get('typeOfRental', [])

            # Find students who applied
            applied_students = [
                {
                    'username': student_data.get('username', 'N/A'),
                    'email': student_data.get('email', 'N/A'),
                    'student_id': student_data.get('student_id', 'N/A'),
                }
                for student_email, student_data in students.items()
                if student_data.get('boardinghouseName') == boardinghouse_name
            ]

            reports.append({
                'boardinghouseName': boardinghouse_name,
                'boardinghouseStatus': boardinghouse_status,
                'ownerName': owner_name,
                'ownerEmail': owner_email,
                'typeOfRental': type_of_rental,
                'appliedStudents': applied_students,
            })

        return render(request, 'generateReports.html', {'reports': reports})

    except Exception as e:
        print(f"Error: {str(e)}")
        messages.error(request, 'An error occurred while generating reports.')
        return redirect('generatingReports')


def generateStudentReports(request):
    context = get_sao_context(request)
    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('sao_login')

    try:
        # Fetch student data
        students_data = db.child('students').get().val() or {}
        reports = []

        for student_email, student_info in students_data.items():
            # Extract the required fields
            username = student_info.get('username', 'N/A')
            student_id = student_info.get('student_id', 'N/A')
            course = student_info.get('course', 'N/A')
            email = student_info.get('email', 'N/A')
            account_status = student_info.get('accountStatus', 'N/A')
            boardinghouse_name = student_info.get('boardinghouseName', 'N/A')

            # Append to reports
            reports.append({
                'username': username,
                'student_id': student_id,
                'course': course,
                'email': email,
                'accountStatus': account_status,
                'boardinghouseName': boardinghouse_name,
            })

        return render(request, 'generateReportsStudent.html', {'reports': reports})

    except Exception as e:
        print(f"Error: {str(e)}")
        messages.error(request, 'An error occurred while generating student reports.')
        return redirect('generateStudentReports')







def saologout(request):
    email = request.session.get('email')  # Get the email from the session
    
    if email:
        # Generate the email key for Firebase
        email_key = email.replace('.', '_').replace('@', '_at_')

        # Fetch the superadmin data using the email to find the correct UID
        superadmin_data = db.child("saoaccounts").child("datas").child("superadmin").order_by_child("email").equal_to(email).get()

        if superadmin_data.each():
            # Get the first matching superadmin
            superadmin_uid = superadmin_data.each()[0].key()  # Get the superadmin UID (key)
            print(f"Found superadmin UID: {superadmin_uid}")  # Debugging statement

            try:
                # Update active_status to 'offline' for the corresponding superadmin
                db.child("saoaccounts").child("datas").child("superadmin").child(superadmin_uid).update({"active_status": "offline"})
                print(f"Active status updated to 'offline' for: {superadmin_uid}")  # Debugging statement
            except Exception as e:
                print(f"Error updating active status for {email}: {str(e)}")
        else:
            print(f"No superadmin found with email: {email}")  # Debugging statement

    # Clear the session data after updating Firebase
    request.session.flush()
    messages.success(request, 'You have successfully logged out.')  # Optional: Add a success message
    return redirect('sao_login')













#This is for Owners
# Dictionary to track owner login attempts
owner_login_attempts = {}

def owner_login(request):
    email = ""  # Initialize email variable

    if request.method == 'POST':
        email = request.POST.get('email')  # Capture the email from the form submission
        password = request.POST.get('password')

        # Initialize or update the dictionary for this email
        if email not in owner_login_attempts:
            owner_login_attempts[email] = {'failed_attempts': 0, 'delay': 0, 'locked_until': None}

        # Check if the email is currently locked
        if owner_login_attempts[email]['locked_until'] and timezone.now() < owner_login_attempts[email]['locked_until']:
            # Email is locked, show error message with remaining time
            remaining_time = (owner_login_attempts[email]['locked_until'] - timezone.now()).seconds
            send_lockout_email(email, remaining_time)  # Send lockout email
            messages.error(request, f"This account is temporarily locked due to too many failed login attempts. Please try again in {remaining_time // 60} minutes and {remaining_time % 60} seconds.")
            return render(request, 'BHOwnerLOGIN.html', {'popup_message': True, 'remaining_time': remaining_time, 'email': email})

        # Get the current number of failed attempts for this email
        failed_attempts = owner_login_attempts[email]['failed_attempts']
        delay = owner_login_attempts[email]['delay']

        # Introduce delay based on the current failed attempts
        if delay > 0:
            time.sleep(delay)  # Progressive delay

        try:
            # Authenticate the user using Firebase
            user = auth_instance.sign_in_with_email_and_password(email, password)

            # Generate the trimmed email key for Firebase
            user_id = email.replace('.', '_').replace('@', '_at_')  # Consistent email key generation

            # Fetch user details from Firebase Realtime Database
            owner_data = db.child('owners').child(user_id).get().val()

            # Check if the user exists
            if owner_data:
                # Check if the role is 'removed'
                if owner_data.get('role') == 'removed':
                    messages.error(request, "Your account has been banned. To contact the administrator, click Report below.")
                    return render(request, 'BHOwnerLOGIN.html', {'email': email})

                # Store necessary details in the session
                request.session['first_name'] = owner_data.get('firstname', 'Owner')
                request.session['profile_picture'] = owner_data.get(
                    'profile_picture',
                    "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4"
                )

                # Store email in session
                request.session['email'] = email
                
                # Fetch role and active_status
                user_role = owner_data.get('role', 'unknown')
                user_active_status = owner_data.get('active_status', 'offline')

                # Call the log_ip_and_url function to log the login details
                ip_address = request.META.get('REMOTE_ADDR', '')  # Get the IP address of the request
                current_url = request.build_absolute_uri()  # Get the current URL
                log_ip_and_url(ip_address, current_url, "owner/owner_login/", user_email=email, user_status="online", user_role=user_role)

                # Save user info in Firebase for monitoring
                user_info = {
                    'identity': email,
                    'active_status': user_active_status,
                    'role': user_role
                }

                # Save user info to Firebase for monitoring
                db.child("fetchedusersIPaddress").child(user_id).update(user_info)

                # Check if the role is 'owner'
                if owner_data.get('role') == 'owner':
                    # Update the active_status to 'online'
                    db.child('owners').child(user_id).update({"active_status": "online"})

                    # Reset the failed attempts on successful login
                    owner_login_attempts[email] = {'failed_attempts': 0, 'delay': 0, 'locked_until': None}

                    # Set timeLoggedOut to 0 and increment daysLogin
                    try:
                        db.child('owners').child(user_id).update({
                            "timeLoggedOut": 0,
                            "daysLogin": owner_data.get('daysLogin', 0) + 1
                        })
                        print("Update successful: timeLoggedOut set to 0")
                    except Exception as e:
                        print(f"Failed to update timeLoggedOut: {str(e)}")

                    messages.success(request, f'Successfully logged in as {request.session["first_name"]}.')
                    return redirect('ownerhomepage')  # Redirect to the owner's dashboard
                else:
                    # If the role is not owner, deny login
                    messages.error(request, 'Unauthorized access. This account is not allowed to login as an Admin.')
                    return render(request, 'BHOwnerLOGIN.html', {'email': email})  # Retain email on failure
            else:
                # User does not exist in the database
                messages.error(request, 'No account found with this email address.')
                return render(request, 'BHOwnerLOGIN.html', {'email': email})  # Retain email on failure

        except Exception as e:
            # Handle login failure
            failed_attempts += 1
            delay = failed_attempts * DELAY_MULTIPLIER
            owner_login_attempts[email]['failed_attempts'] = failed_attempts
            owner_login_attempts[email]['delay'] = delay

            if failed_attempts >= MAX_ATTEMPTS:
                lock_until = timezone.now() + timezone.timedelta(seconds=LOCK_TIME)
                owner_login_attempts[email]['locked_until'] = lock_until
                owner_login_attempts[email]['failed_attempts'] = 0
                messages.error(request, "Too many failed attempts. Your account has been temporarily locked.")
                send_lockout_email(email, LOCK_TIME)  # Send lockout email with the lock time
            else:
                messages.error(request, "Invalid email or password.")

            return render(request, 'BHOwnerLOGIN.html', {'email': email})  # Retain email on failure

    return render(request, 'BHOwnerLOGIN.html', {'email': email})  # Ensure email is passed when rendering




def owner_forgotpassword(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        birthday = request.POST.get('birthday')

        # Transform the email to match how it's stored in Firebase
        email_key = email.replace('.', '_').replace('@', '_at_')

        try:
            # Fetch the owner data from Firebase
            owner_data = db.child("owners").child(email_key).get()

            # Check if owner exists
            if owner_data.val() is None:
                error_message = "Owner account not found."
                return render(request, 'owner_forgotpassword.html', {'error_message': error_message})

            # Get owner data
            owner_data = owner_data.val()

            # Check if the birthday matches
            if owner_data.get('birthday') != birthday:
                error_message = "Owner account not found."
                return render(request, 'owner_forgotpassword.html', {'error_message': error_message})

            # Send password reset email using Pyrebase
            auth_instance.send_password_reset_email(email)

            success_message = f"A password reset link has been sent to {email}."
            return render(request, 'owner_forgotpassword.html', {'success_message': success_message})

        except Exception as e:
            error_message = f"An unexpected error occurred while processing your request. Please try again later. (Error: {str(e)})"
            return render(request, 'owner_forgotpassword.html', {'error_message': error_message})

    return render(request, 'owner_forgotpassword.html')




def ownerSignUpFirstStep(request):
    email = request.POST.get('email', '')  # Get the email even if not submitted yet

    if request.method == 'POST': 
        firstname = request.POST.get('firstname')   
        middlename = request.POST.get('middlename')
        lastname = request.POST.get('lastname')
        extension = request.POST.get('extension')
        gender = request.POST.get('gender')
        address = request.POST.get('address')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')
        phone_number = request.POST.get('phone-number')
        birthday = request.POST.get('birthday')  # Get the birthday from the form
        profile_picture = request.FILES.get('profilePicture')  # Get the uploaded profile picture

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'OwnerSignUp-FirstStep.html')

        try:
            # Create user in Firebase Authentication
            user = auth_instance.create_user_with_email_and_password(email, password)
            otp, otp_hash = generate_otp()
            otp_expiry = int(time.time()) + 300
            print(f"Sending OTP code: {otp}")  # This line prints the OTP to the console
            
            # Generate the email key
            email_key = email.replace('.', '_').replace('@', '_at_')  # Consistent email key generation
            
            # Default profile picture URL
            default_profile_img_url = "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4"

            # Handle profile picture upload if a file was uploaded
            if profile_picture:
                profile_picture_name = profile_picture.name  # Get the original file name
                profile_picture_path = f'owners_profilepicture/{email_key}/{profile_picture_name}'  # Create the path
                storage.child(profile_picture_path).put(profile_picture)  # Upload the picture
                print(f"Profile picture uploaded to {profile_picture_path}")  # Debugging line
                profile_picture_url = storage.child(profile_picture_path).get_url(None)  # Get the public URL
            else:
                profile_picture_url = default_profile_img_url  # Use default image if none uploaded

            # Get the current date and time in the desired format
            signup_time = datetime.now().strftime('%B %d, %Y %I:%M %p')

            # User data to store in Firebase Realtime Database
            owner_data = {
                "firstname": firstname,
                "middlename": middlename,
                "lastname": lastname,
                "extension": extension,
                "gender": gender,
                "address": address,
                "email": email,
                "phone_number": phone_number,
                "birthday": birthday,  # Save the birthday in the database
                "status": "pending",
                "verification_code": otp_hash,
                "otp_expiry": otp_expiry,
                "profile_picture": profile_picture_url,
                "role": "owner",
                "accountStatus": "pending",
                "active_status": "offline",  # Set default status to 'offline'
                "signup_time": signup_time,  # Add signup time
                "timeLoggedOut": 0,  # Initialize timeLoggedOut to 0
                "daysLogin": 0  # Initialize daysLogin to 0
            }

            # Save owner data in Firebase Realtime Database
            db.child("owners").child(email_key).set(owner_data)
            print(f"Owner data saved to Firebase: {owner_data}")  # Debugging line

            # Send OTP to the user
            send_otp_email(email, otp)
            
            # Set session data
            request.session['owner_data'] = {'email': email}

            messages.success(request, 'Account created successfully. Please verify your account.')
            return redirect('ownerVerifyOtp')

        except Exception as e:
            error_message = str(e)
            print(f"Exception occurred: {error_message}")  # Debugging line
            if "EMAIL_EXISTS" in error_message:
                messages.error(request, 'An account with this email already exists. Please use a different email.')
            else:
                messages.error(request, f'Error creating account: {error_message}')
    
    return render(request, 'BHOwnerSignUp-FirstStep.html')

 

def owner_verify_otp(email, input_otp):
    try:
        # Fetch owner data based on email
        owner_data = db.child("owners").order_by_child("email").equal_to(email).get().val()
        
        if not owner_data:
            return False, "Owner data not found."

        owner_id, owner_info = next(iter(owner_data.items()))

        # Check if OTP has expired
        if int(time.time()) > owner_info['otp_expiry']:
            return False, "The OTP has expired. Please request a new one."

        # Verify OTP
        otp_hash = owner_info.get('verification_code')
        input_otp_hash = hashlib.sha256(str(input_otp).encode()).hexdigest()

        if otp_hash == input_otp_hash:
            # Update the status to 'verified' in Firebase
            db.child("owners").child(owner_id).update({"status": "verified"})
            return True, "OTP verified successfully."
        else:
            return False, "Invalid OTP. Please try again."
    except Exception as e:
        return False, f"Error verifying OTP: {str(e)}"


def ownerVerifyOtp(request):
    if request.method == 'POST':
        email = request.session.get('owner_data', {}).get('email')
        if not email:
            messages.error(request, "Session expired. Please create an account again.")
            return redirect('ownerSignUpFirstStep')

        input_otp = request.POST.get('otp')
        action = request.POST.get('action', 'verify')

        if action == 'verify':
            is_valid, message = owner_verify_otp(email, input_otp)
            if is_valid:
                messages.success(request, message)
                return redirect('owner_login')
            else:
                messages.error(request, message)

        elif action == 'resend':
            try:
                otp, otp_hash = generate_otp()
                otp_expiry = int(time.time()) + 300
                owner_data = db.child("owners").order_by_child("email").equal_to(email).get().val()
                if owner_data:
                    owner_id, _ = next(iter(owner_data.items()))
                    db.child("owners").child(owner_id).update({"verification_code": otp_hash, "otp_expiry": otp_expiry})
                    send_otp_email(email, otp)
                    messages.success(request, 'OTP resent successfully. Please check your email.')
                else:
                    messages.error(request, "No owner data found to resend OTP.")
            except Exception as e:
                messages.error(request, f"Error resending OTP: {str(e)}")

    return render(request, 'OwnerVerifyOtp.html')
    
    
def ownerSignUpSecondStep(request):
    context = get_owner_context(request)

    if context is None:
        messages.error(request, 'User is not logged in. Please log in again.')
        return redirect('owner_login')

    email_key = context['email'].replace('.', '_').replace('@', '_at_')

    # Fetch existing owner data
    firebase_data = db.child('ownersBoardingHouse').child(email_key).get().val()
    
    # If there's existing data, it will override the context
    if firebase_data:
        saved_owner_data = firebase_data
    else:
        saved_owner_data = {}

    current_status = saved_owner_data.get('boardinghouseStatus', 'pending')

    # Set the boardinghouseStatus based on the existing value
    if current_status == 'approved':
        boardinghouse_status = 'approved'  # Keep it approved if already approved
    else:
        boardinghouse_status = 'pending'  # Default to pending for new submissions

    if request.method == 'POST':
        # Fetch data from form fields
        boardinghouse_name = request.POST.get('boardinghouseName')
        about_us = request.POST.get('aboutUs')
        amenities = request.FILES.getlist('amenities[]')
        documents = request.FILES.getlist('documents[]')
        rooms = request.POST.getlist('rooms[]')
        capacities = request.POST.getlist('capacity[]')
        prices = request.POST.getlist('price[]')
        aircon_statuses = request.POST.getlist('aircon[]')
        room_images = request.FILES.getlist('room_images[]')
 
        # New fields
        wifi_available = request.POST.get('wifiAvailable')
        free_electric_bill = request.POST.get('freeElectricBill')
        free_water_bill = request.POST.get('freeWaterBill')
        type_of_rental = request.POST.getlist('rentalType[]')
        parking_space = request.POST.get('parkingSpace')
        toilet_Available = request.POST.get('toiletAvailable')

        # Separate security feature values
        securityFeatures_keys = request.POST.get('securityFeatures_keys')
        securityFeatures_curfew = request.POST.get('securityFeatures_curfew')
        securityFeatures_cctv = request.POST.get('securityFeatures_cctv')

        # Safety Protocols
        emergency_Exit = request.POST.get('emergencyExit')
        fire_Extinguishers = request.POST.get('fireExtinguishers') 

        default_cover_photo_url = "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9"
        cover_photo = request.FILES.get('coverPhoto')

        # Determine the cover photo URL
        if cover_photo:
            try:
                upload_path = f'documents/boardinghouseimgs/{email_key}/coverphoto/{cover_photo.name}'
                storage.child(upload_path).put(cover_photo)
                cover_photo_url = storage.child(upload_path).get_url(None)
            except Exception as e:
                print("Error uploading cover photo:", e)
                cover_photo_url = saved_owner_data.get('coverPhoto', default_cover_photo_url)
        else:
            # Use existing cover photo if no new cover photo is uploaded
            cover_photo_url = saved_owner_data.get('coverPhoto', default_cover_photo_url)

        fullname = f"{context.get('firstname', '')} {context.get('middlename', '')} {context.get('lastname', '')}".strip()
        # Check if boardinghouseName is being changed
        if saved_owner_data and saved_owner_data.get('boardinghouseName') and saved_owner_data['boardinghouseName'] != boardinghouse_name:
            # If there's already a boardinghouseName set and it's being changed, display error
            messages.error(request, "Boardinghouse name cannot be changed once it has been set.")
            return redirect('ownerSignUpSecondStep')  # Redirect back to the same page or wherever necessary

        owner_data = {
            'name': fullname,
            'boardinghouseName': boardinghouse_name,
            'aboutUs': about_us,
            'coverPhoto': cover_photo_url,
            'profile_picture': context.get('profile_picture'),
            'amenities': [],  # Start with empty list for amenities
            'documents': [],   # Start with empty list for documents
            'rooms': [],       # Start with empty list for rooms
            'wifiAvailable': wifi_available,
            'freeElectricBill': free_electric_bill,
            'freeWaterBill': free_water_bill,
            'toiletAvailable': toilet_Available,
            'typeOfRental': type_of_rental,
            'parkingSpace': parking_space,
            'securityFeatures_keys': securityFeatures_keys,
            'securityFeatures_curfew': securityFeatures_curfew,
            'securityFeatures_cctv': securityFeatures_cctv,
            'emergencyExit': emergency_Exit,
            'fireExtinguishers': fire_Extinguishers,
            'boardinghouseStatus': boardinghouse_status,
            'email': context['email']  # Include email here
        }

        # Preserve existing students applied data if any
        existing_students_applied = saved_owner_data.get('studentsapplied', [])
        owner_data['studentsapplied'] = existing_students_applied  # Set existing studentsapplied to owner_data


        if 'ratings' in saved_owner_data:
            owner_data['ratings'] = saved_owner_data['ratings']

        # Preserve existing amenities if any
        existing_amenities = saved_owner_data.get('amenities', [])
        owner_data['amenities'] = existing_amenities  # Set existing amenities to owner_data

        # Save new amenities and merge with existing ones
        for amenity in amenities:
            amenity_path = f'documents/boardinghouseimgs/{email_key}/amenities/{amenity.name}'
            try:
                storage.child(amenity_path).put(amenity)
                amenity_url = storage.child(amenity_path).get_url(None)
                owner_data['amenities'].append(amenity_url)  # Append new amenity URLs
            except Exception as e:
                print("Error uploading amenity:", e)

        # Preserve existing documents if any
        existing_documents = saved_owner_data.get('documents', [])
        owner_data['documents'] = existing_documents  # Set existing documents to owner_data

        # Save documents in Firebase
        for document in documents:
            document_path = f'documents/boardinghouseimgs/{email_key}/documents/{document.name}'
            try:
                storage.child(document_path).put(document)
                document_url = storage.child(document_path).get_url(None)
                owner_data['documents'].append(document_url)  # Append new document URLs
            except Exception as e:
                print("Error uploading document:", e)

        # Preserve existing rooms if any
        existing_rooms = saved_owner_data.get('rooms', [])
        
        default_room_image_url = "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FbhdefaultImg.jpg?alt=media&token=840762fb-fd74-4b8a-9576-ccff59a636b6"

        for i in range(len(rooms)):
            room_data = {
                'roomName': rooms[i],
                'capacity': capacities[i] if i < len(capacities) else None,
                'price': prices[i] if i < len(prices) else None,
                'aircon': aircon_statuses[i] if i < len(aircon_statuses) else None,
                'images': [],
                'availabilityStatus': "AVAILABLE"
            }

            # Check if a room image is available, else use the default image
            if i < len(room_images) and room_images[i]:
                room_image = room_images[i]
                room_image_path = f'documents/boardinghouseimgs/{email_key}/rooms/{rooms[i]}/{room_image.name}'
                try:
                    storage.child(room_image_path).put(room_image)
                    room_image_url = storage.child(room_image_path).get_url(None)
                except Exception as e:
                    print("Error uploading room image:", e)
                    room_image_url = default_room_image_url  # Use default if there's an error
            else:
                room_image_url = default_room_image_url  # Use default if no image is uploaded

            room_data['images'].append(room_image_url)  # Append the image URL (default or uploaded)
            existing_rooms.append(room_data)  # Append new room data to existing rooms

        owner_data['rooms'] = existing_rooms  # Update owner_data with merged room list


        # Save owner data in Firebase
        db.child('ownersBoardingHouse').child(email_key).set(owner_data)

        # Fetch the saved data to include in the context
        saved_owner_data = db.child('ownersBoardingHouse').child(email_key).get().val()
        messages.success(request, 'Owner details saved successfully!')
        
    # Render the template with both context and saved_owner_data
    return render(request, 'BHOwnerSignUp-SecondStep.html', {
        'context': context,
        'saved_owner_data': saved_owner_data
    })




# View to handle form rendering
def location_form(request):
    context = get_owner_context(request)

    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')

    return render(request, "location_form.html", context)

@csrf_exempt
def save_location(request):
    if request.method == "POST":
        try:
            # Get the logged-in owner's email from the session via context
            context = get_owner_context(request)
            if context is None:
                messages.error(request, "Owner not logged in.")
                return JsonResponse({"error": "Owner not logged in."}, status=400)

            owner_email = context['email']
            owner_email_key = owner_email.replace('.', '_').replace('@', '_at_')

            # Parse JSON data from the request body
            data = json.loads(request.body)
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            country = data.get("country")
            province = data.get("province")
            road = data.get("road")

            # Check if all required fields are present
            if not all([latitude, longitude, country, province, road]):
                messages.error(request, "All fields are required.")
                return JsonResponse({"error": "All fields are required."}, status=400)

            # Save data to Firebase under "user_locations/owner_email_key/details"
            location_ref = db.child("user_locations").child(owner_email_key).child("details")
            location_ref.set({
                "latitude": latitude,
                "longitude": longitude,
                "country": country,
                "province": province,
                "road": road,
            })

            # Add success message
            messages.success(request, "Location saved successfully!")
            return JsonResponse({"message": "Location saved successfully!"}, status=200)

        except Exception as e:
            # Add error message
            messages.error(request, f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == "GET":
        try:
            context = get_owner_context(request)
            print("Context:", context)
            if context is None:
                print("Context is None. Owner not logged in.")
                messages.error(request, "Owner not logged in.")
                return JsonResponse({"error": "Owner not logged in."}, status=400)

            owner_email = context['email']
            print("Owner Email:", owner_email)

            owner_email_key = owner_email.replace('.', '_').replace('@', '_at_')
            print("Owner Email Key:", owner_email_key)

            location_ref = db.child("user_locations").child(owner_email_key).child("details")
            print("Firebase Reference Path:", location_ref.path)

            location_data = location_ref.get()
            print("Raw Fetched Data:", location_data)

            if location_data.exists():
                print("Fetched Location Data:", location_data.val())
                return JsonResponse(location_data.val(), status=200)
            else:
                print("No location data found for the user.")
                return JsonResponse({"message": "No location data found."}, status=404)

        except Exception as e:
            print("Error while fetching location data:", str(e))
            messages.error(request, f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)







def view_images(request):
    context = get_owner_context(request)

    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')
    
    # Extract email key from the session
    email = request.session.get("email")
    if not email:
        return render(request, "error.html", {"message": "Session email not found."})

    email_key = email.replace(".", "_").replace("@", "_at_")

    # Fetch amenities and documents from Firebase
    owner_data = db.child("ownersBoardingHouse").child(email_key).get().val() or {}
    amenities = owner_data.get("amenities", [])
    documents = owner_data.get("documents", [])

    # Handle image removal if there is an image URL passed in the request
    image_url_to_remove = request.GET.get('remove_image')
    if image_url_to_remove:
        # Remove the image from amenities or documents
        if image_url_to_remove in amenities:
            db.child("ownersBoardingHouse").child(email_key).update({
                'amenities': [image for image in amenities if image != image_url_to_remove]
            })
        elif image_url_to_remove in documents:
            db.child("ownersBoardingHouse").child(email_key).update({
                'documents': [image for image in documents if image != image_url_to_remove]
            })
        # Optionally show a success message
        messages.success(request, "Image has been removed successfully.")
        return redirect('view_images')  # Redirect to the same page to see the updated list

    # Prepare context to pass to the template
    context = {
        "amenities": amenities,
        "documents": documents,
        **context,
    }

    return render(request, "view_images.html", context)




def ownersRoomManagement(request):
    context = get_owner_context(request)

    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')

    # Fetch the owner email directly from the context
    owner_email = context['email']
    email_key = owner_email.replace('.', '_').replace('@', '_at_')

    # Path for owner data
    owner_path = f'ownersBoardingHouse/{email_key}'
    owner_data = db.child(owner_path).get().val()

    # Fetch rooms data
    rooms_data = owner_data.get('rooms', []) if owner_data else []

    available_rooms = sum(
        1 for room in rooms_data 
        if room.get('availabilityStatus') == 'AVAILABLE' and room.get('status') != 'notShown'
    )
    not_available_rooms = sum(
        1 for room in rooms_data 
        if room.get('availabilityStatus') == 'ROOM FULL' and room.get('status') != 'notShown'
    )
    # Fetch the boardinghouseName
    boardinghouse_name = owner_data.get('boardinghouseName') if owner_data else None
    if not boardinghouse_name:
        print("[DEBUG] Boardinghouse name not found.")
        messages.warning(request, "Boardinghouse name not found.")

    # Fetch all removal requests for students under ownersBoardingHouseRequest
    removal_request_path = "ownersBoardingHouseRequest"
    removal_request_data = db.child(removal_request_path).get().val()

    # Handle all removal requests
    filtered_requests = []
    if removal_request_data:
        all_requests = (
            list(removal_request_data.values()) 
            if isinstance(removal_request_data, dict) 
            else removal_request_data
        )

        for req in all_requests:
            if (
                'boardinghouseName' in req 
                and 'status' in req 
                and req['boardinghouseName'] == boardinghouse_name 
                and req['status'] == "pending"
            ):
                filtered_requests.append(req)



    # Handle room addition logic
    if request.method == 'POST':  
        # Check if the form is for approving a removal request
        if 'approve_request' in request.POST:
            # Get form data
            boardinghouse_name = request.POST.get('boardinghouseName')
            student_email = request.POST.get('studentEmail')

            # Generate the Firebase-compatible email keys
            student_email_key = student_email.replace('.', '_').replace('@', '_at_')
            owner_email = request.POST.get('ownerEmail')  # Fetch owner email from session
            owner_email_key = owner_email.replace('.', '_').replace('@', '_at_') if owner_email else None

            if not owner_email_key:
                messages.error(request, "Owner email not found in session. Please log in again.")
                return redirect('owner_login')

            # Path to the specific student's removal request
            removal_request_path = f"ownersBoardingHouseRequest/{student_email_key}"

            # Fetch the removal request for the student
            removal_request = db.child(removal_request_path).get().val()

            # Validate and update the removal request
            if removal_request:
                if (
                    removal_request.get('boardinghouseName') == boardinghouse_name and
                    removal_request.get('status') == "pending"
                ):
                    # Update the status to "approved"
                    db.child(removal_request_path).update({'status': 'approved'})

                    # Path to the student's data in the 'students' node
                    student_path = f"students/{student_email_key}"

                    # Fetch the student's data to get the roomName
                    student_data = db.child(student_path).get().val()
                    if student_data:
                        room_name = student_data.get('roomName', '')

                        # Remove the specific nodes
                        nodes_to_remove = ['appliedRoomStatus', 'boardinghouseName', 'roomName', 'schedule_date']
                        for node in nodes_to_remove:
                            if node in student_data:
                                db.child(f"{student_path}/{node}").remove()

                        # --- Update numberStayingIn ---
                        rooms_path = f"ownersBoardingHouse/{owner_email_key}/rooms"
                        boarding_house_rooms = db.child(rooms_path).get().val()

                        if boarding_house_rooms:
                            if isinstance(boarding_house_rooms, list):
                                # Iterate through the list
                                for room_index, room_data in enumerate(boarding_house_rooms):
                                    if room_data.get('roomName') == room_name:
                                        # Ensure current_staying is an integer
                                        current_staying = int(room_data.get('numberStayingIn', 0))  # Convert to int if not already
                                        updated_staying = max(current_staying - 1, 0)  # Ensure it doesn't go below 0

                                        updates = {'numberStayingIn': updated_staying}

                                        # Ensure capacity is an integer
                                        capacity = int(room_data.get('capacity', 0))  # Convert to int if not already
                                        if updated_staying < capacity:
                                            updates['availabilityStatus'] = "AVAILABLE"

                                        # Update the room
                                        db.child(rooms_path).child(str(room_index)).update(updates)

                            elif isinstance(boarding_house_rooms, dict):
                                # Iterate through the dictionary
                                for room_key, room_data in boarding_house_rooms.items():
                                    if room_data.get('roomName') == room_name:
                                        # Ensure current_staying is an integer
                                        current_staying = int(room_data.get('numberStayingIn', 0))  # Convert to int if not already
                                        updated_staying = max(current_staying - 1, 0)  # Ensure it doesn't go below 0

                                        updates = {'numberStayingIn': updated_staying}

                                        # Ensure capacity is an integer
                                        capacity = int(room_data.get('capacity', 0))  # Convert to int if not already
                                        if updated_staying < capacity:
                                            updates['availabilityStatus'] = "AVAILABLE"
                                        
                                        # Update the room
                                        db.child(rooms_path).child(room_key).update(updates)


                                        # Update the room
                                        db.child(rooms_path).child(room_key).update(updates)

                    # Path to the student's applied data in the owner's node
                    student_applied_path = f"ownersBoardingHouse/{owner_email_key}/studentsapplied/{student_email_key}"

                    # Fetch the student's applied data
                    student_applied_data = db.child(student_applied_path).get().val()
                    if student_applied_data and 'applyStatus' in student_applied_data:
                        # Remove the applyStatus node if it exists
                        db.child(f"{student_applied_path}/applyStatus").remove()

                    # --- Notification Logic ---
                    notifications = db.child("students").child(student_email_key).child("notifications").get().val() or {}
                    notification_count = len(notifications) + 1

                    # Create the notification message
                    notification_message = f"Your application for removal in {boardinghouse_name} has now been approved. Thank you for staying!"

                    # Format the current date and time
                    time_of_notification = datetime.now().strftime("%B %d, %Y %I:%M %p")

                    # Add new notification with both message and timestamp
                    db.child("students").child(student_email_key).child("notifications").child(f"notification{notification_count}").set({
                        "message": notification_message,
                        "time_of_notification": time_of_notification
                    })

                    messages.success(request, f"Removal request for {student_email} has been approved and relevant data has been removed. Notification sent to the student.")
                else:
                    messages.error(request, "No matching pending removal request found.")
            else:
                messages.error(request, f"No removal request found for {student_email}.")

            return redirect('ownersRoomManagement')




        if 'updateRooms' in request.POST:
            # Retrieve form data
            room_name = request.POST.get('roomName')
            room_capacity = request.POST.get('capacity')
            room_price = request.POST.get('price')
            room_type = request.POST.get('aircon')
            number_staying_in = request.POST.get('numberStayingIn')

            # Ensure all fields are valid
            if not (room_name and room_capacity and room_price and room_type and number_staying_in):
                messages.error(request, "All fields are required.")
                return redirect('ownersRoomManagement')

            # Convert values to appropriate types
            try:
                room_capacity = int(room_capacity)
                number_staying_in = int(number_staying_in)
                room_price = float(room_price)
            except ValueError:
                messages.error(request, "Invalid input data. Please check your values.")
                return redirect('ownersRoomManagement')

            # Ensure room_type is valid
            if room_type not in ['Aircon', 'Non-Aircon']:
                messages.error(request, "Invalid room type selected. Please select 'Aircon' or 'Non-Aircon'.")
                return redirect('ownersRoomManagement')

            # Validate capacity
            if number_staying_in > room_capacity:
                messages.error(request, "The number of people staying cannot exceed the room's capacity.")
                return redirect('ownersRoomManagement')

            # Find the room to update
            room_to_update = None
            for room in rooms_data:
                if room.get('roomName') == room_name:
                    room_to_update = room
                    break

            if not room_to_update:
                messages.error(request, "Room not found.")
                return redirect('ownersRoomManagement')

            # Update room details
            room_to_update['roomName'] = room_name
            room_to_update['capacity'] = room_capacity
            room_to_update['price'] = room_price
            room_to_update['aircon'] = room_type
            room_to_update['numberStayingIn'] = number_staying_in

            # Determine room availability status
            if number_staying_in < room_capacity:
                room_status = "AVAILABLE"
            elif number_staying_in == room_capacity:
                room_status = "ROOM FULL"
            else:
                room_status = "Overbooked"

            room_to_update['availabilityStatus'] = room_status

            # Save updated data back to Firebase
            db.child(f"{owner_path}/rooms").set(rooms_data)
            messages.success(request, f"Room '{room_name}' updated successfully!")
            return redirect('ownersRoomManagement')




        if 'unhideRoom' in request.POST:
            unhide_room_name = request.POST.get('unhideRoomName')
            if unhide_room_name:
                for room in rooms_data:
                    if room.get('roomName') == unhide_room_name and room.get('status') == 'notShown':
                        room['status'] = 'shown'  # Update status to 'shown'
                        break
                owner_data['rooms'] = rooms_data  # Update the rooms list
                db.child(owner_path).set(owner_data)  # Save changes to Firebase
                messages.success(request, f'Room "{unhide_room_name}" is now visible.')
            else:
                messages.error(request, "Room not found or already visible.")

            return redirect('ownersRoomManagement')

        if 'hide_room' in request.POST:
            room_name = request.POST.get('room_name')
            if room_name:
                for room in rooms_data:
                    if room.get('roomName') == room_name:
                        room['status'] = 'notShown'  # Update the status
                        break
                owner_data['rooms'] = rooms_data  # Update the room data
                db.child(owner_path).set(owner_data)  # Save changes to Firebase
                messages.success(request, f'Room "{room_name}" is now marked as not shown.')
            else:
                messages.error(request, "Room not found.")

            return redirect('ownersRoomManagement')

        # Retrieve form data for room addition
        room_name = request.POST.get('room_name')
        room_capacity = request.POST.get('room_capacity')
        room_price = request.POST.get('room_price')
        room_type = request.POST.get('room_type')
        room_image = request.FILES.get('room_image')

        # Default room image URL
        default_room_image_url = "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FbhdefaultImg.jpg?alt=media&token=840762fb-fd74-4b8a-9576-ccff59a636b6"

        # Initialize room data
        room_data = {
            'roomName': room_name,
            'capacity': room_capacity,
            'price': room_price,
            'aircon': room_type,
            'images': [],
            'availabilityStatus': "AVAILABLE"
        }

        # Upload room image or use default
        if room_image:
            room_image_path = f'documents/boardinghouseimgs/{email_key}/rooms/{room_name}/{room_image.name}'
            try:
                storage.child(room_image_path).put(room_image)
                room_image_url = storage.child(room_image_path).get_url(None)
            except Exception as e:
                print("Error uploading room image:", e)
                room_image_url = default_room_image_url  # Use default if there's an error
        else:
            room_image_url = default_room_image_url  # Use default if no image is uploaded

        # Add image URL to room data
        room_data['images'].append(room_image_url)

        # Append new room data to existing rooms
        rooms_data.append(room_data)

        # Update owner data with merged room list
        owner_data['rooms'] = rooms_data
        db.child(owner_path).set(owner_data)

        messages.success(request, f"Room '{room_name}' added successfully!")
        return redirect('ownersRoomManagement')

    # Count rooms with status "notShown"
    not_shown_rooms_count = sum(1 for room in rooms_data if room.get('status') == 'notShown')

    # Count total rooms added
    total_rooms_count = len(rooms_data)
    room_status = request.session.get('room_status', 'AVAILABLE')
    # Update context with rooms data, filtered removal requests, boardinghouseName, and counts
    context.update({
        'rooms': rooms_data,
        'removal_requests': filtered_requests,
        'boardinghouse_name': boardinghouse_name,
        'not_shown_rooms_count': not_shown_rooms_count,   
        'total_rooms_count': total_rooms_count,
        'available_rooms': available_rooms,   
        'not_available_rooms': not_available_rooms
    })

    return render(request, 'Owners-manageRoom.html', context)




def update_room(request):
    if request.method == 'POST':
        # Retrieve form data
        room_name = request.POST.get('roomName')
        room_capacity = request.POST.get('capacity')
        room_price = request.POST.get('price')
        room_type = request.POST.get('aircon')
        number_staying_in = request.POST.get('numberStayingIn')

        # Ensure all fields are valid
        if not (room_name and room_capacity and room_price and room_type and number_staying_in):
            messages.error(request, "All fields are required.")
            return redirect('ownersRoomManagement')

        # Convert values to appropriate types
        try:
            room_capacity = int(room_capacity)
            number_staying_in = int(number_staying_in)
            room_price = float(room_price)
        except ValueError:
            messages.error(request, "Invalid input data. Please check your values.")
            return redirect('ownersRoomManagement')

        # Ensure that room_type is 'Aircon' or 'Non-Aircon'
        if room_type not in ['Aircon', 'Non-Aircon']:
            messages.error(request, "Invalid room type selected. Please select 'Aircon' or 'Non-Aircon'.")
            return redirect('ownersRoomManagement')

        # Validate that the number staying in doesn't exceed capacity
        if number_staying_in > room_capacity:
            messages.error(request, "The number of people staying cannot exceed the room's capacity.")
            return redirect('ownersRoomManagement')

        # Fetch the owner and room data from Firebase
        email_key = request.POST.get('email_key')  # Assuming you're storing email_key in the session
        email_key = email_key.replace('@', '_at_').replace('.', '_')  # Format the email key

        # Construct the owner path
        owner_path = f'ownersBoardingHouse/{email_key}/rooms'  # Firebase path for rooms
        owner_data = db.child(owner_path).get().val()  # Fetch data from Firebase

        # Find the room to update (using room_name)
        room_to_update = None
        if isinstance(owner_data, list):
            for room in owner_data:
                if room.get('roomName') == room_name:
                    room_to_update = room
                    break

        if not room_to_update:
            messages.error(request, "Room not found.")
            return redirect('ownersRoomManagement')

        # Update room details
        room_to_update['roomName'] = room_name
        room_to_update['capacity'] = room_capacity
        room_to_update['price'] = room_price
        room_to_update['aircon'] = room_type
        room_to_update['numberStayingIn'] = number_staying_in

        # Determine room availability status
        if number_staying_in < room_capacity:
            room_status = "AVAILABLE"
        elif number_staying_in == room_capacity:
            room_status = "ROOM FULL"
        else:
            room_status = "Overbooked"  # Optional, in case numberStayingIn exceeds capacity

        # Save room availability status
        room_to_update['availabilityStatus'] = room_status  # Add availability status to the room data

        # Save updated data back to Firebase
        db.child(owner_path).set(owner_data)  # Updating rooms in the owner path (overwrite the entire list)
        messages.success(request, f"Room '{room_name}' updated successfully!")

        # Store the availability status in session to be used on the next request
        request.session['room_status'] = room_status

        # Redirect back to the room management page
        return redirect('ownersRoomManagement')  # Ensure this route is defined in your URLs

    else:
        return redirect('ownersRoomManagement')




def ownersTenantsManagement(request):
    context = get_owner_context(request)
    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')

    owner_email = context.get('email')
    owner_email_key = owner_email.replace('.', '_').replace('@', '_at_') if owner_email else None

    if not owner_email_key:
        messages.error(request, 'Owner email not found in session. Please log in again.')
        return redirect('owner_login')

    owner_path = f"ownersBoardingHouse/{owner_email_key}"
    owner_data = db.child(owner_path).get().val()
    owner_boardinghouse_name = owner_data.get('boardinghouseName') if owner_data else None

    if not owner_boardinghouse_name:
        messages.error(request, 'Your boarding house name is not set up. Please update your profile.')
        return redirect('ownersProfileSetup')

    # Fetch rejected students
    students_applied_path = f"{owner_path}/studentsapplied"
    students_applied_data = db.child(students_applied_path).get().val()

    print(f"Fetched Data: {students_applied_data}")  # Debugging

    rejected_students = []

    if students_applied_data:
        for student_email_key, rooms in students_applied_data.items():
            # Check if 'rooms' is a dictionary
            if isinstance(rooms, dict):
                for room_key, student_info in rooms.items():  # Iterate through nested room keys
                    print(f"Checking student: {student_email_key} -> Room: {room_key} -> {student_info}")  # Debugging
                    if isinstance(student_info, dict) and student_info.get('status') == 'rejected':  # Ensure student_info is a dictionary
                        rejected_students.append({
                            'email_key': student_email_key,
                            'roomName': student_info.get('roomName'),
                            'status': student_info.get('status'),
                            'username': student_info.get('username'),
                            'profile_picture': student_info.get('profile_picture'),
                            'rejection_reason': student_info.get('rejection_reason', 'N/A'),  # Optional reason
                        })
            else:
                print(f"Invalid room data for student {student_email_key}: {rooms}")  # Debugging invalid structure

    print(f"Rejected Students: {rejected_students}")  # Debugging

    context['rejected_students'] = rejected_students
    context['rejected_students_count'] = len(rejected_students)
 



    if request.method == "POST":
        student_id = request.POST.get("student_id")
        email = request.POST.get("email")
        removal_reason = request.POST.get("removalReason")

        if not student_id or not email or not removal_reason:
            messages.error(request, "Student ID, email, or removal reason is missing.")
        else:
            try:
                email_key = email.replace('.', '_').replace('@', '_at_')
                student_path = f"students/{email_key}"
                student_data = db.child(student_path).get().val()

                if not student_data:
                    messages.error(request, "Student not found.")
                else:
                    room_name = student_data.get("roomName", "")
                    fields_to_remove = ["boardinghouseName", "roomName", "schedule_date", "appliedRoomStatus"]

                    # Remove specific fields
                    for field in fields_to_remove:
                        db.child(f"{student_path}/{field}").remove()

                    # Add removal details
                    db.child(student_path).update({
                        "removalReason": removal_reason,
                        "removalDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                    # Remove application status
                    student_applied_path = f"ownersBoardingHouse/{owner_email_key}/studentsapplied/{email_key}"
                    db.child(f"{student_applied_path}/applyStatus").remove()

                    # Update room information
                    rooms_path = f"ownersBoardingHouse/{owner_email_key}/rooms"
                    boarding_house_rooms = db.child(rooms_path).get().val()

                    if boarding_house_rooms:
                        for room_key, room_data in (boarding_house_rooms.items() if isinstance(boarding_house_rooms, dict) else enumerate(boarding_house_rooms)):
                            if room_data.get("roomName") == room_name:
                                # Ensure 'numberStayingIn' is an integer
                                number_staying_in = int(room_data.get("numberStayingIn", 0))  # Convert to integer
                                updated_staying = max(number_staying_in - 1, 0)

                                # Ensure 'capacity' is an integer
                                capacity = int(room_data.get("capacity", 0))  # Convert to integer
                                
                                updates = {"numberStayingIn": updated_staying}
                                if updated_staying < capacity:
                                    updates["availabilityStatus"] = "AVAILABLE"
                                
                                db.child(rooms_path).child(room_key).update(updates)

                    # Add notification
                    notifications = db.child("students").child(email_key).child("notifications").get().val() or {}
                    notification_count = len(notifications) + 1
                    notification_message = (
                        f"You have been removed from {owner_boardinghouse_name} due to: {removal_reason}. "
                        "For more details, contact the management. Thank you."
                    )
                    db.child("students").child(email_key).child("notifications").child(f"notification{notification_count}").set({
                        "message": notification_message,
                        "time_of_notification": datetime.now().strftime("%B %d, %Y %I:%M %p")
                    })

                    # Send email notification
                    email_subject = "Notice of Removal from Boarding House"
                    email_body = f"""
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <link href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" rel="stylesheet">
                        <style>
                            body {{
                                font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
                                background-color: #f8d7da;
                                margin: 0;
                                padding: 40px 20px;
                                color: #721c24;
                                line-height: 1.6;
                            }}
                            .envelope {{
                                max-width: 600px;
                                margin: 0 auto;
                                background: linear-gradient(145deg, #ffffff 0%, #f3f4f6 100%);
                                border-radius: 16px;
                                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
                                overflow: hidden;
                                position: relative;
                            }}
                            .envelope::before {{
                                content: '';
                                position: absolute;
                                top: 0;
                                left: 0;
                                right: 0;
                                height: 6px;
                                background: linear-gradient(90deg, #d9534f, #c9302c);
                            }}
                            .header {{
                                background: linear-gradient(135deg, #d9534f, #c9302c);
                                color: white;
                                padding: 2rem;
                                text-align: center;
                            }}
                            .header h2 {{
                                margin: 0;
                                font-size: 1.75rem;
                                font-weight: 700;
                            }}
                            .content {{
                                padding: 2rem;
                            }}
                            .removal-badge {{
                                background: linear-gradient(135deg, #c9302c, #ac2925);
                                color: white;
                                font-size: 1.5rem;
                                font-weight: 700;
                                padding: 0.75rem 2rem;
                                border-radius: 999px;
                                display: inline-block;
                                margin: 1rem 0;
                                text-transform: uppercase;
                            }}
                            .removal-message {{
                                margin: 1rem 0;
                                font-size: 1.25rem;
                                font-weight: 600;
                                color: #d9534f;
                                text-align: center;
                            }}
                            .details-section {{
                                background-color: #f8d7da;
                                border-radius: 12px;
                                padding: 1.5rem;
                                margin: 1.5rem 0;
                                border: 1px solid #f5c6cb;
                            }}
                            .details-list {{
                                list-style: none;
                                padding: 0;
                            }}
                            .details-list li {{
                                margin-bottom: 1rem;
                            }}
                            .footer {{
                                text-align: center;
                                padding: 2rem;
                                background: linear-gradient(180deg, #f5c6cb 0%, #f1b0b7 100%);
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="envelope">
                            <div class="header">
                                <h2>Notice of Removal</h2>
                            </div>
                            <div class="content">
                                <center>
                                    <div class="removal-badge">Removed</div>
                                </center>
                                <div class="removal-message">
                                    You have been removed from: <strong>{owner_boardinghouse_name}</strong>
                                </div>
                                <p>Dear {student_data.get('username', 'Student')},</p>
                                <p>We regret to inform you that your association with the boarding house has been terminated due to the following reason:</p>
                                <p><strong>{removal_reason}</strong></p>
                                <div class="details-section">
                                    <h3>Details</h3>
                                    <ul class="details-list">
                                        <li><strong>Boarding House Name:</strong> {owner_boardinghouse_name}</li>
                                        <li><strong>Room:</strong> {student_data.get('roomName', 'N/A')}</li>
                                    </ul>
                                </div>
                                <p>If you have any questions or require further clarification, please do not hesitate to contact the boarding house management.</p>
                            </div>
                            <div class="footer">
                                <p>Best regards,</p>
                                <p>{owner_boardinghouse_name} Owner</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """

                    try:
                        send_mail(
                            email_subject,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                            html_message=email_body
                        )
                        messages.success(request, f"Student {email} has been removed. Notification sent via email and system.")
                    except Exception as email_error:
                        print(f"Error sending email: {email_error}")
                        messages.warning(request, f"Student {email} has been removed, but the email notification could not be sent.")

            except Exception as e:
                print(f"Error removing student: {e}")
                messages.error(request, f"An error occurred while removing the student: {str(e)}")

    students_path = "students"
    all_students = db.child(students_path).get().val()
    matched_students = []

    if all_students:
        for student_email_key, student_data in all_students.items():
            if student_data.get('boardinghouseName') == owner_boardinghouse_name:
                matched_students.append({
                    'boardinghouseName': student_data.get('boardinghouseName'),
                    'roomName': student_data.get('roomName'),
                    'username': student_data.get('username'),
                    'student_id': student_data.get('student_id'),
                    'profile_picture': student_data.get('profile_picture'),
                    'email': student_data.get('email')
                })

    context['matched_students'] = matched_students
    context['student_count'] = len(matched_students)

    return render(request, 'Owner-TenantsManagement.html', context)



def delete_conversationOwner(request, superadmin_email):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "owner/ownerhomepage/delete_conversationOwner")
    
    owner_context = get_owner_context(request)
    if owner_context is None:  # User is not logged in
        return redirect('owner_login')

    sanitized_from_owner = sanitize_path_part(owner_context['email'])
    sanitized_superadmin_email = sanitize_path_part(superadmin_email)

    messages_path = f'messages/{sanitized_from_owner}-{sanitized_superadmin_email}'

    # Delete messages if they exist
    messages_data = db.child(messages_path).get()
    if messages_data.val() is not None:
        db.child(messages_path).remove()
        print(f"Messages deleted successfully from: {messages_path}")
    else:
        print(f"No messages found for deletion at path: {messages_path}")

    # Redirect back to the same conversation with the query parameter
    return redirect(f'/owner/ownerhomepage/message_owner?superadmin_email={superadmin_email}')





def message_owner(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "owner/ownerhomepage/owner_message")

    owner_context = get_owner_context(request)
    if owner_context is None:  # User is not logged in
        return redirect('owner_login')

    # Fetch superadmins
    superadmin_data = db.child('saoaccounts').child('datas').child('superadmin').get()
    superadmin_list = []

    if superadmin_data and superadmin_data.each():
        for item in superadmin_data.each():
            uid = item.key()
            superadmin_info = {
                'name': item.val().get('name', 'No Name'),
                'email': item.val().get('email', 'No Email'),
                'profileImage': item.val().get('profileImage', 'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4'),
                'activeStatus': item.val().get('active_status', 'offline')
            }
            if uid.startswith('superadmin'):
                superadmin_list.append(superadmin_info)

    if request.method == 'POST':
        if 'delete' in request.POST:  # Handle delete functionality
            current_superadmin_email = request.POST.get('superadmin_email')

            if not current_superadmin_email:
                return redirect('owner_message')

            # Call the delete function
            delete_conversationOwner(request, current_superadmin_email)

            # Redirect back to the conversation page
            return redirect(f'{request.path}?superadmin_email={current_superadmin_email}')
        else:  # Handle sending messages
            message = request.POST.get('message')
            from_owner = owner_context['email']
            to_superadmin = request.POST.get('to_superadmin_email')

            if not from_owner or not to_superadmin:
                return redirect('owner_message')

            sanitized_from_owner = sanitize_path_part(from_owner)
            sanitized_to_superadmin = sanitize_path_part(to_superadmin)

            encrypted_message = vigenere_encrypt(message, 'DATALINK')
            message_uid = str(uuid4())

            message_data = {
                'from': from_owner,
                'to': to_superadmin,
                'message': encrypted_message,
                'timestamp': datetime.now().strftime('%B %d, %Y %I:%M %p')
            }

            message_path = f'messages/{sanitized_from_owner}-{sanitized_to_superadmin}/{message_uid}'
            db.child(message_path).set(message_data)

            # After sending the message, reload the page
            return redirect(f'{request.path}?superadmin_email={to_superadmin}')

    # Initialize sanitized_from_owner early to avoid unbound variable error
    sanitized_from_owner = None

    # Fetch messages for the owner-superadmin conversation
    messages = []
    current_superadmin_email = request.GET.get('superadmin_email')

    if current_superadmin_email:
        sanitized_from_owner = sanitize_path_part(owner_context['email'])
        sanitized_current_superadmin_email = sanitize_path_part(current_superadmin_email)

        path_1 = f'messages/{sanitized_from_owner}-{sanitized_current_superadmin_email}'
        path_2 = f'messages/{sanitized_current_superadmin_email}-{sanitized_from_owner}'

        for path in [path_1, path_2]:
            messages_data = db.child(path).get()
            if messages_data and messages_data.each():
                for msg in messages_data.each():
                    message_data = msg.val()
                    decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                    messages.append({
                        'from': message_data['from'],
                        'message': decrypted_message,
                        'timestamp': message_data['timestamp']
                    })

    selected_superadmin = next((superadmin for superadmin in superadmin_list if superadmin['email'] == current_superadmin_email), None)
    messages.sort(key=lambda msg: msg['timestamp'], reverse=False)

    # Track the current number of messages
    previous_message_count = len(messages)

    # If the request is an AJAX request, return the messages without reloading the page
    if request.is_ajax():
        return JsonResponse({'messages': messages})

    # Show modal if messages limit is reached
    show_modal = len(messages) >= 15

    context = {
        'selected_superadmin': selected_superadmin,
        'superadmin_list': superadmin_list,
        'messages': messages,
        'current_superadmin_email': current_superadmin_email,
        'show_modal': show_modal,
        **owner_context,
    }

    return render(request, 'message-owner.html', context)


















def ownerSignUpThirdStep(request):
    return render(request, 'BHOwnerSignUp-ThirdStep.html')

def ownerSignUpFourthStep(request):
    return render(request, 'BHOwnerSignUp-FourthStep.html')


def get_owner_context(request):
    # Retrieve first name and profile picture from session
    #greeting = get_greeting()
    firstname = request.session.get('first_name', 'Owner')
    profile_picture = request.session.get(
        'profile_picture',
        'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4'
    )  # Fallback if profile picture isn't available

    # Retrieve email from session
    email = request.session.get('email')
    active_status = 'offline'  # Default to offline
    lastname = ''
    middlename = ''
    account_status = 'inactive'  # Default account status
    pending_students_count = 0  # Default to 0 for pending students
    days_login = 0  # Initialize daysLogin for the owner

    if not email:
        return None  # Indicate that email was not found

    # Consistent email key generation
    email_key = email.replace('.', '_').replace('@', '_at_')

    try:
        # Fetch owner data from Firebase
        owner_data = db.child('owners').child(email_key).get().val()
        if owner_data:
            active_status = owner_data.get('active_status', 'offline')
            lastname = owner_data.get('lastname', '')  # Fetch lastname
            middlename = owner_data.get('middlename', '')  # Fetch middlename
            account_status = owner_data.get('accountStatus', 'inactive')  # Fetch accountStatus
            days_login = owner_data.get('daysLogin', 0)  # Fetch daysLogin for the owner

            # Fetch the students' applications data
            students_applied_data = db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').get().val()
            if students_applied_data:
                # Iterate through each student's data and check the status of their room application
                for student in students_applied_data.values():
                    for room_name, room_data in student.items():
                        # If the status is 'pending', increment the count
                        if room_data.get('status') == 'pending':
                            pending_students_count += 1

            # Update session with latest owner data
            request.session['user_data'] = owner_data
            request.session['first_name'] = owner_data.get('firstname', 'Owner')  # Update first name in session
            request.session['profile_picture'] = owner_data.get('profile_picture', profile_picture)  # Update profile picture in session

    except Exception as e:
        # Handle any errors with fetching data
        print(f"Error fetching data from Firebase: {e}")

    # Prepare context dictionary
    context = {
        'firstname': firstname,
        'profile_picture': profile_picture,
        'email': email,
        'active_status': active_status,
        'lastname': lastname,
        'middlename': middlename,
        'account_status': account_status,  # Include accountStatus in the context
        'pending_students_count': pending_students_count,  # Include the count of pending students
        'daysLogin': days_login,  # Include daysLogin in the context
        #'greeting': greeting,
    }

    return context

 
@csrf_exempt  # Only if CSRF token is manually handled in the script
def update_days_login_owner(request):
    if request.method == 'POST':
        try:
            # Use get_owner_context to fetch the owner's context
            owner_context = get_owner_context(request)
            if not owner_context:
                return JsonResponse({'error': 'Owner context could not be retrieved'}, status=400)

            # Extract email from the context
            email = owner_context.get('email')
            if not email:
                return JsonResponse({'error': 'Email not found in context'}, status=400)

            # Generate Firebase key
            email_key = email.replace('.', '_').replace('@', '_at_')

            # Update the `daysLogin` field in Firebase
            db.child("owners").child(email_key).update({'daysLogin': owner_context['daysLogin'] + 1})
            messages.success(request, "Tour is done! Now, let's showcase your boarding house to students by updating its details.")
            # Return a success response
            return JsonResponse({'message': 'daysLogin updated successfully'})
        except Exception as e:
            # Handle errors gracefully
            return JsonResponse({'error': str(e)}, status=500)

    # Return a method not allowed response if the request is not POST
    return JsonResponse({'error': 'Invalid request method'}, status=405)





def ownerhomepage(request):
    context = get_owner_context(request)

    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')  # Redirect to login page or any appropriate page

    context['active_page'] = 'dashboard'  # Specific active page for homepage

    # Fetch existing owner data
    email_key = context['email'].replace('.', '_').replace('@', '_at_')
    saved_owner_data = db.child('ownersBoardingHouse').child(email_key).get().val()

    # Initialize room counters
    available_rooms = 0
    total_displayed_rooms = 0

    if saved_owner_data:
        rooms = saved_owner_data.get('rooms', [])

        # Filter out rooms with 'notShown' status
        displayed_rooms = [room for room in rooms if room.get('status') != 'notShown']
        total_displayed_rooms = len(displayed_rooms)

        # Count rooms with 'AVAILABLE' in availabilityStatus
        available_rooms = sum(1 for room in displayed_rooms if room.get('availabilityStatus') == 'AVAILABLE')

    # Calculate the percentage of available rooms
    availability_percentage = (available_rooms / total_displayed_rooms * 100) if total_displayed_rooms > 0 else 0

    # Fetch cover photo URL
    cover_photo_url = saved_owner_data.get('coverPhoto') if saved_owner_data else None

    # Fetch the location data
    try:
        location_ref = db.child("user_locations").child(email_key).child("details")
        location_data = location_ref.get().val()

        if location_data:
            print("Fetched location data:", location_data)  # Debug: Log the fetched location data
            context['location_data'] = location_data
        else:
            print("No location data found for the user.")
            context['location_data'] = None
    except Exception as e:
        print(f"Error fetching location data: {str(e)}")
        context['location_data'] = None

    # Add data to context
    context['total_displayed_rooms'] = total_displayed_rooms
    context['available_rooms'] = available_rooms
    context['availability_percentage'] = round(availability_percentage, 2)
    context['cover_photo_url'] = cover_photo_url

    # Debug: Print the context before rendering
    print(f"Context passed to template: {context}")

    return render(request, 'Owner-Homepage.html', context)






def owner_homeReport(request):
    # Log IP address and URL for debugging or analytics purposes
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "owner/ownerhomepage/owner_report_problem")

    # Fetch context data for the logged-in owner
    context = get_owner_context(request)

    if context is None:  # Handle missing email in session
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')

    # Extract the necessary details from the context
    email = context.get('email', '')
    firstname = context.get('firstname', '')
    lastname = context.get('lastname', '')
    full_name = f"{firstname} {lastname}"

    # Include owner details in the context for the template
    owner_details = {
        'email': email,
        'fullname': full_name,
    }

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Format email key for Firebase query
        email_key = email.replace('.', '_').replace('@', '_at_')

        try:
            # Check if the email exists in the 'owners' table in Firebase
            owner_data = db.child("owners").child(email_key).get()

            if owner_data.val():
                # If email exists, proceed with saving the report
                date_of_report = datetime.now().strftime("%B %d, %Y %I:%M %p")

                report_data = {
                    "name": name,
                    "email": email,
                    "message": message,
                    "date_of_report": date_of_report,
                    "status": "unfixed"
                }

                # Save the report data under the email_key in messages
                db.child("usersReport").child("owners").child(email_key).child("messages").push(report_data)
                messages.success(request, 'Your report has been sent. Please wait for the response.')
            else:
                # If email doesn't exist, show error
                messages.error(request, 'Only the owners with account registered can report.')

        except Exception as e:
            error_message = str(e)
            print(f"Exception occurred: {error_message}")  # Debugging
            messages.error(request, f'Error processing your request: {error_message}')

        return redirect('owner_homeReport')

    return render(request, 'owner-homeReport.html', {**context, **owner_details})






def ownerlodger(request):
    context = get_owner_context(request)

    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')

    # Retrieve the owner's email from the context
    owner_email = context.get('email')
    if owner_email:
        email_key = owner_email.replace('.', '_').replace('@', '_at_')

        try:
            # Handle form submission for approval or rejection
            if request.method == "POST":
                student_id = request.POST.get("student_id")  
                room_name = request.POST.get("room_name")

                if 'approve_application' in request.POST:
                    schedule_date = request.POST.get("schedule_date")

                    if student_id and room_name and schedule_date:
                        try:
                            parsed_date = datetime.strptime(schedule_date, "%Y-%m-%d").date()
                            today = datetime.today().date()

                            # Check if schedule_date is today or beyond
                            if parsed_date < today:
                                messages.error(request, "Date should be today or beyond.")
                            else:
                                # Fetch the applied room status from the students database
                                student_email_key = student_id.replace('.', '_').replace('@', '_at_')
                                appliedRoomStatus = db.child("students").child(student_email_key).child('appliedRoomStatus').get().val()

                                # Check if the appliedRoomStatus is already approved
                                if appliedRoomStatus == 'approved':
                                    messages.error(request, "This student is already approved by someone else. You can remove this student.")
                                    return redirect('ownerlodger')  # Redirect to prevent further processing

                                # Fetch all room applications for the student
                                rooms = db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_id).get().val()

                                if isinstance(rooms, dict):
                                    # Update all other room applications to cancelled
                                    for other_room_name, application_data in rooms.items():
                                        if other_room_name != room_name:  # Skip the approved room
                                            db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_id).child(other_room_name).update({
                                                "status": "cancelled"
                                            })

                                    # Update status and add schedule date in Firebase for the approved room
                                    db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_id).child(room_name).update({
                                        "status": "approved",
                                        "schedule_date": schedule_date
                                    })

                                    # Update the student's database with boardinghouseName, roomName, and schedule_date
                                    boardinghouse_name = rooms[room_name].get('boardinghouseName', '')  # Get boarding house name

                                    db.child("students").child(student_email_key).update({
                                        "boardinghouseName": boardinghouse_name,
                                        "roomName": room_name,
                                        "schedule_date": schedule_date,
                                        "appliedRoomStatus": "approved"
                                    })

                                    

                                    # Increment numberStayingIn for the specific room
                                    # Fetch the rooms of the boarding house
                                    boarding_house_rooms = db.child('ownersBoardingHouse').child(email_key).child('rooms').get().val()

                                    if boarding_house_rooms:
                                        # Check if boarding_house_rooms is a list or a dictionary
                                        if isinstance(boarding_house_rooms, list):
                                            # Iterate through the list
                                            for room_index, room_data in enumerate(boarding_house_rooms):
                                                # Check if the roomName matches the approved room
                                                if room_data.get("roomName") == room_name:
                                                    # Ensure current_number_staying_in is an integer
                                                    current_number_staying_in = int(room_data.get("numberStayingIn", 0))  # Convert to int if not already
                                                    updated_number_staying_in = current_number_staying_in + 1

                                                    # Ensure room_capacity is an integer
                                                    room_capacity = int(room_data.get("capacity", 0))  # Convert to int if not already

                                                    updates = {"numberStayingIn": updated_number_staying_in}

                                                    # Check if the room is full
                                                    if updated_number_staying_in >= room_capacity:
                                                        updates["availabilityStatus"] = "ROOM FULL"

                                                    # Update the room's numberStayingIn and possibly availabilityStatus
                                                    db.child('ownersBoardingHouse').child(email_key).child('rooms').child(str(room_index)).update(updates)

                                        if isinstance(boarding_house_rooms, dict):
                                            for room_key, room_data in boarding_house_rooms.items():
                                                # Ensure current_number_staying_in is an integer
                                                current_number_staying_in = int(room_data.get("numberStayingIn", 0))  # Convert to int if not already
                                                updated_number_staying_in = current_number_staying_in + 1
                                                
                                                # Ensure room_capacity is an integer
                                                room_capacity = int(room_data.get("capacity", 0))  # Convert to int if not already

                                                updates = {"numberStayingIn": updated_number_staying_in}

                                                # Check if the room is full
                                                if updated_number_staying_in >= room_capacity:
                                                    updates["availabilityStatus"] = "ROOM FULL"

                                                db.child('ownersBoardingHouse').child(email_key).child('rooms').child(room_key).update(updates)

                                    else:
                                        print("No rooms found for this boarding house.")





                                    # Set applyStatus to "approved" directly under the student_id
                                    db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_id).update({
                                        "applyStatus": "approved"
                                    })

                                    # Add a notification under the student's data
                                    notifications = db.child("students").child(student_email_key).child("notifications").get().val() or {}
                                    notification_count = len(notifications) + 1

                                    # Create the notification message
                                    notification_message = f"Your application to {boardinghouse_name} room {room_name} has now been approved. See your email for your identification when meeting the owner."

                                    # Format the current date and time
                                    time_of_notification = datetime.now().strftime("%B %d, %Y %I:%M %p")

                                    # Add new notification with both message and timestamp
                                    db.child("students").child(student_email_key).child("notifications").child(f"notification{notification_count}").set({
                                        "message": notification_message,
                                        "time_of_notification": time_of_notification
                                    })

                                    # --- Send Email to Student ---
                                    owner_data = db.child('ownersBoardingHouse').child(email_key).get().val()
                                    if owner_data: 
                                        owner_name = owner_data.get('name', '')
                                        student_email = request.POST.get("student_email") 

                                        email_subject = "Your Room Application Has Been Approved"
                                        html_message = f"""
                                        <!DOCTYPE html>
                                        <html lang="en">
                                        <head>
                                            <meta charset="UTF-8">
                                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                            <link href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" rel="stylesheet">
                                            <style>
                                                body {{
                                                    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
                                                    background-color: #e5e7eb;
                                                    margin: 0;
                                                    padding: 40px 20px;
                                                    color: #1f2937;
                                                    line-height: 1.6;
                                                }}
                                                .envelope {{
                                                    max-width: 600px;
                                                    margin: 0 auto;
                                                    background: linear-gradient(145deg, #ffffff 0%, #f3f4f6 100%);
                                                    border-radius: 16px;
                                                    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
                                                    overflow: hidden;
                                                    position: relative;
                                                }}
                                                .envelope::before {{
                                                    content: '';
                                                    position: absolute;
                                                    top: 0;
                                                    left: 0;
                                                    right: 0;
                                                    height: 6px;
                                                    background: linear-gradient(90deg, #1e40af, #3b82f6);
                                                }}
                                                .header {{
                                                    background: linear-gradient(135deg, #1e40af, #3b82f6);
                                                    color: white;
                                                    padding: 2rem;
                                                    text-align: center;
                                                }}
                                                .header h2 {{
                                                    margin: 0;
                                                    font-size: 1.75rem;
                                                    font-weight: 700;
                                                }}
                                                .content {{
                                                    padding: 2rem;
                                                }}
                                                .approval-badge {{
                                                    background: linear-gradient(135deg, #059669, #10b981);
                                                    color: white;
                                                    font-size: 1.5rem;
                                                    font-weight: 700;
                                                    padding: 0.75rem 2rem;
                                                    border-radius: 999px;
                                                    display: inline-block;
                                                    margin: 1rem 0;
                                                    text-transform: uppercase;
                                                }}
                                                .schedule-message {{
                                                    margin: 1rem 0;
                                                    font-size: 1.25rem;
                                                    font-weight: 600;
                                                    color: #1e40af;
                                                    text-align: center;
                                                }}
                                                .details-section {{
                                                    background-color: #f8fafc;
                                                    border-radius: 12px;
                                                    padding: 1.5rem;
                                                    margin: 1.5rem 0;
                                                    border: 1px solid #d1d5db;
                                                }}
                                                .details-list {{
                                                    list-style: none;
                                                    padding: 0;
                                                }}
                                                .details-list li {{
                                                    margin-bottom: 1rem;
                                                }}
                                                .footer {{
                                                    text-align: center;
                                                    padding: 2rem;
                                                    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
                                                }}
                                            </style>
                                        </head>
                                        <body>
                                            <div class="envelope">
                                                <div class="header">
                                                    <h2>Room Application Approved</h2>
                                                </div>
                                                <div class="content">
                                                    <center>
                                                        <div class="approval-badge">Approved</div>
                                                    </center>
                                                    <div class="schedule-message">
                                                        You are scheduled to come: <strong>{schedule_date}</strong>
                                                    </div>
                                                    <p>Dear Student,</p>
                                                    <p>Your application for the room at <strong>{boardinghouse_name}</strong> has been approved.</p>
                                                    <div class="details-section">
                                                        <h3>Details</h3>
                                                        <ul class="details-list">
                                                            <li><strong>Boarding House Name:</strong> {boardinghouse_name}</li>
                                                            <li><strong>Room:</strong> {room_name}</li> 
                                                            <li><strong>Owner Name:</strong> {owner_name}</li>
                                                        </ul>
                                                    </div>
                                                    <p>Please check your email for identification when meeting the owner.</p>
                                                </div>
                                                <div class="footer">
                                                    <p>Best regards,</p>
                                                    <p>Boarding House Owner</p>
                                                </div>
                                            </div>
                                        </body>
                                        </html>
                                        """

                                        # Send the email
                                        email = EmailMessage(
                                            email_subject,
                                            html_message,
                                            settings.EMAIL_HOST_USER,  # Sender email
                                            [student_email],  # Recipient email
                                        )
                                        email.content_subtype = "html"  # Specify email type as HTML
                                        email.send(fail_silently=False)

                                    messages.success(request, f"Application for student ID {student_id} has been approved and email has been sent.")
                                else:
                                    messages.error(request, "No room applications found for this student.")
                        except ValueError:
                            messages.error(request, "Invalid date format. Please select a valid date.")
                    else:
                        messages.error(request, "Please provide a schedule date for student's expectation to come.")

                # Remove Application 
                elif 'remove_application' in request.POST:
                    if student_id and room_name:
                        student_email_key = student_id.replace('.', '_').replace('@', '_at_')
                        rejection_reason = request.POST.get("rejection_reason")

                        # Update the status of the specified room application to "rejected" and save the reason
                        db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_id).child(room_name).update({
                            "status": "rejected",
                            "rejection_reason": rejection_reason
                        })

                        # Add a notification under the student's data
                        notifications = db.child("students").child(student_email_key).child("notifications").get().val() or {}
                        notification_count = len(notifications) + 1

                        # Create the notification message
                        notification_message = f"Your application to {room_name} has been rejected."
                        if rejection_reason:
                            notification_message += f" Reason: {rejection_reason}"

                        # Format the current date and time
                        time_of_notification = datetime.now().strftime("%B %d, %Y %I:%M %p")

                        # Add new notification with both message and timestamp
                        db.child("students").child(student_email_key).child("notifications").child(f"notification{notification_count}").set({
                            "message": notification_message,
                            "time_of_notification": time_of_notification
                        })

                        messages.success(request, f"Application for room '{room_name}' by student ID {student_id} has been rejected.")
                    else:
                        messages.error(request, "Missing room name or student ID for rejection.")



            # Fetch all students applied data from Firebase
            studentsapplied = db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').get().val()

            if isinstance(studentsapplied, dict):
                pending_applications = []

                for student_email_key, rooms in studentsapplied.items():
                    if isinstance(rooms, dict):
                        for room_name, application_data in rooms.items():
                            if isinstance(application_data, dict) and application_data.get('status') == 'pending':
                                pending_applications.append({
                                    "boardinghouseName": application_data.get('boardinghouseName', ''),
                                    "email": application_data.get('email', ''),
                                    "roomName": room_name,
                                    "username": application_data.get('username', ''),
                                    "student_id": student_email_key,
                                    "course": application_data.get('course', ''),
                                    "gender": application_data.get('gender', ''),
                                    "profile_picture": application_data.get('profile_picture', ''),
                                    "coverPhoto": application_data.get('coverPhoto', ''),
                                    "time_applied": application_data.get('time_applied', ''),
                                    "status": application_data.get('status', ''),
                                    "boardinghouseOwnerEmail": application_data.get('boardinghouseOwnerEmail', '')
                                })
                context['pending_applications'] = pending_applications
            else:
                context['pending_applications'] = []

        except Exception as e:
            messages.error(request, f"Error fetching applications: {str(e)}")
            context['pending_applications'] = []
    else:
        context['pending_applications'] = []

    context['active_page'] = 'lodger'
    return render(request, 'Owner-Lodger.html', context)






def ownerfeedback(request):
    # Get the context for the owner
    context = get_owner_context(request)

    if context is None:  # Check if email was not found
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')

    # Fetch feedback from Firebase
    email_key = context.get('email')  # Assuming 'email' is in the context
    if email_key:
        email_key = email_key.replace('.', '_').replace('@', '_at_')

        try:
            # Retrieve all feedback from the ratings path
            feedback_data = db.child('ownersBoardingHouse').child(email_key).child('ratings').get()
            feedback_list = []
            total_students = 0  # Initialize total students counter

            if feedback_data.each():
                # Iterate over each feedback and collect data
                for feedback in feedback_data.each():
                    feedback_info = feedback.val()
                    feedback_list.append({
                        'profile_picture': feedback_info.get('profile_picture'),
                        'username': feedback_info.get('username'),
                        'rating': feedback_info.get('rating'),
                        'student_id': feedback_info.get('student_id'),
                        'role': feedback_info.get('role')
                    })
                    total_students += 1  # Increment the counter for each feedback entry

                # Calculate the average rating
                ratings = [float(fb['rating']) for fb in feedback_list if fb['rating'] is not None]
                average_rating = sum(ratings) / len(ratings) if ratings else 0
            else:
                average_rating = 0

            # Round the average rating
            average_rating = round(average_rating, 2)

            # Determine feedback description
            if average_rating == 1:
                feedback_description = "Needs Significant Improvement"
            elif average_rating == 2:
                feedback_description = "Below Expectations"
            elif average_rating == 3:
                feedback_description = "Satisfactory Performance"
            elif average_rating == 4:
                feedback_description = "Very Good Performance"
            elif average_rating == 5:
                feedback_description = "Exceptional Performance"
            else:
                feedback_description = "No Feedback Available"

            # Store feedback data, average rating, total students, and description in the context
            context['feedback_list'] = feedback_list
            context['average_rating'] = average_rating
            context['feedback_description'] = feedback_description
            context['total_students'] = total_students  # Add total students to the context

        except Exception as e:
            messages.error(request, f"Error fetching feedback: {str(e)}")
            context['feedback_list'] = []  # Default to empty list on error
            context['average_rating'] = 0
            context['feedback_description'] = "No Feedback Available"
            context['total_students'] = 0  # Default to 0 on error
    else:
        context['feedback_list'] = []  # Default to empty list if email key is missing
        context['average_rating'] = 0
        context['feedback_description'] = "No Feedback Available"
        context['total_students'] = 0  # Default to 0 if email key is missing

    context['active_page'] = 'feedback'  # Specific active page for feedback
    return render(request, 'Owner-Feedback.html', context)



def ownersettings(request):
    # Get owner context
    context = get_owner_context(request)

    if context is None:
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('owner_login')

    context['active_page'] = 'Ownersettings'
    
    if request.method == 'GET':
        # Fetch owner data from Firebase
        email = context.get('email')
        user_id = email.replace('.', '_').replace('@', '_at_')  # Consistent email key generation
        owner_data = db.child('owners').child(user_id).get().val()

        if owner_data:
            # Ensure phone_number starts with +639
            phone_number = owner_data.get('phone_number', '')
            if not phone_number.startswith('+639'):
                phone_number = f"+639{phone_number.lstrip('0')}"
            context['phone_number'] = phone_number

            # Get address, gender, and birthday
            context['address'] = owner_data.get('address', '')
            context['gender'] = owner_data.get('gender', '')
            context['birthday'] = owner_data.get('birthday', '')  # Fetch birthday

            # Fetch other fields
            context['firstname'] = owner_data.get('firstname', '')
            context['middlename'] = owner_data.get('middlename', '')
            context['lastname'] = owner_data.get('lastname', '')
            context['profile_picture'] = owner_data.get('profile_picture', '')
            
            try:
                email_key = context['email'].replace('.', '_').replace('@', '_at_')
                saved_owner_data = db.child('ownersBoardingHouse').child(email_key).get().val()
                print(f"Fetched owner data: {saved_owner_data}")  # Debug output
                if saved_owner_data:
                    context['boardinghouse_name'] = saved_owner_data.get('boardinghouseName', 'No boarding house assigned')
                    print(f"Boardinghouse name found: {context['boardinghouse_name']}")  # Debug output
                else:
                    context['boardinghouse_name'] = 'No boarding house data available'
                    print("No data found for the provided email key")  # Debug output
            except Exception as e:
                print(f"Error fetching boardinghouseName: {e}")
                context['boardinghouse_name'] = 'Error fetching boarding house'


            # Check if feedback was already submitted
            existing_feedback = db.child('usersReport').child('saofeedback').child('owners').child(user_id).get()
            context['feedback_submitted'] = existing_feedback.val() is not None and 'star_rating' in existing_feedback.val()

        return render(request, 'Owner-Settings.html', context)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'star_rating_update':
            # Handle star rating update
            star_rating = request.POST.get('star_rating')
            try:
                # Validate the star rating (should be between 1 and 5)
                if not star_rating or not star_rating.isdigit() or not 1 <= int(star_rating) <= 5:
                    messages.error(request, "Please select a valid star rating.")
                    return redirect('ownersettings')

                email = context.get('email')
                user_id = email.replace('.', '_').replace('@', '_at_')  # Consistent email key generation

                # Fetch the existing feedback for the user
                existing_feedback = db.child('usersReport').child('saofeedback').child('owners').child(user_id).get()

                # Check if feedback already exists
                if existing_feedback.val() and 'star_rating' in existing_feedback.val():
                    messages.error(request, "You have already submitted feedback.")
                    return redirect('ownersettings')

                # Fetch additional user information
                owner_data = db.child('owners').child(user_id).get().val()  # Get owner's data
                if owner_data:
                    # Prepare the name and additional data
                    firstname = owner_data.get('firstname', '')
                    middlename = owner_data.get('middlename', '')
                    lastname = owner_data.get('lastname', '')
                    role = owner_data.get('role', '')  # Assuming 'role' is stored in the database
                    profile_picture = owner_data.get('profile_picture', '')  # Assuming profile_picture is stored

                    # Concatenate names
                    name = f"{firstname} {middlename} {lastname}".strip()

                    # Save the star rating and additional data in Firebase
                    db.child('usersReport').child('saofeedback').child('owners').child(user_id).update({
                        'star_rating': int(star_rating),
                        'email': email,
                        'role': role,
                        'profile_picture': profile_picture,
                        'name': name  # Save the concatenated name
                    })

                    # Mark feedback as submitted
                    context['feedback_submitted'] = True
                    messages.success(request, f"Star rating updated to {star_rating} stars!")

                else:
                    messages.error(request, "Owner data not found.")
                    return redirect('ownersettings')

            except Exception as e:
                messages.error(request, f"Error saving star rating: {str(e)}")
                return redirect('ownersettings')


        if form_type == 'profile_update':
            # Existing profile update logic
            firstname = request.POST.get('firstname')
            middlename = request.POST.get('middlename')
            lastname = request.POST.get('lastname')
            gender = request.POST.get('gender')
            address = request.POST.get('address')
            phone_number = request.POST.get('phone_number')
            birthday = request.POST.get('birthday')  # Capture birthday

            # Handle profile picture upload
            profile_picture = request.FILES.get('profile_picture')

            # Validation
            if not firstname or not lastname or not address or not phone_number or not birthday:
                messages.error(request, "All required fields must be filled.")
                return redirect('ownersettings')

            # Validate birthday (between 1900 and 2010)
            try:
                birthday_year = int(birthday.split('-')[0])
                if birthday_year < 1900 or birthday_year > 2010:
                    messages.error(request, "Birthday must be between 1900 and 2010.")
                    return redirect('ownersettings')
            except ValueError:
                messages.error(request, "Invalid birthday format.")
                return redirect('ownersettings')

            # Validate phone number
            if not phone_number.startswith('+639') or len(phone_number) != 13:
                messages.error(request, "Phone number must start with +639 and be 11 digits in total.")
                return redirect('ownersettings')

            try:
                email = context.get('email')
                user_id = email.replace('.', '_').replace('@', '_at_')

                # Default profile picture URL
                default_profile_img_url = "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4"

                # Check if a new profile picture was uploaded
                if profile_picture:
                    # Handle profile picture upload
                    profile_picture_name = profile_picture.name  # Get the original file name
                    profile_picture_path = f'owners_profilepicture/{user_id}/{profile_picture_name}'  # Create the path
                    storage.child(profile_picture_path).put(profile_picture)  # Upload the picture
                    profile_picture_url = storage.child(profile_picture_path).get_url(None)  # Get the public URL
                else:
                    # Use existing or default profile picture
                    profile_picture_url = context.get('profile_picture', default_profile_img_url)

                # Prepare the updated data
                updated_data = {
                    "firstname": firstname,
                    "middlename": middlename,
                    "lastname": lastname,
                    "gender": gender,
                    "address": address,
                    "phone_number": phone_number,
                    "birthday": birthday,  # Save the birthday
                    "profile_picture": profile_picture_url  # Save the profile picture URL
                }

                # Update Firebase with new data
                db.child('owners').child(user_id).update(updated_data)

                # Fetch the updated owner data
                updated_owner = db.child('owners').child(user_id).get().val()   

                if updated_owner:
                    # Update session with new data
                    request.session['user_data'] = updated_owner  # Update session with new data
                    request.session['first_name'] = updated_owner.get('firstname', 'Owner')  # Update first name
                    request.session['profile_picture'] = updated_owner.get('profile_picture', default_profile_img_url)  # Update profile picture

                messages.success(request, "Profile updated successfully!")
                return redirect('ownersettings')  # Redirect after successful update

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
                return redirect('ownersettings')



        elif form_type == 'password_update':
            current_password = request.POST.get('currentPassword')
            new_password = request.POST.get('newPassword')
            confirm_password = request.POST.get('confirmPassword')
            email = context.get('email')  # Assuming you have the email in context

            # Validate inputs
            if not current_password or not new_password or not confirm_password:
                messages.error(request, "All password fields are required.")
                return render(request, 'Owner-Settings.html', context)

            if new_password != confirm_password:
                messages.error(request, "New password and confirm password do not match.")
                return render(request, 'Owner-Settings.html', context)

            try:
                # Re-authenticate the user
                user = auth_instance.sign_in_with_email_and_password(email, current_password)
                id_token = user['idToken']

                # Use Firebase REST API to update the password
                firebase_api_key = "AIzaSyAfCuib-Q7FmAlr9oj9CIwBONeMkWnpdgU"  # Replace with your actual Firebase API key
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={firebase_api_key}"

                data = {
                    'idToken': id_token,
                    'password': new_password,
                    'returnSecureToken': True
                }

                # Make the API request to update the password
                response = requests.post(url, json=data)
                response_data = response.json()

                if response.status_code == 200:
                    messages.success(request, "Password updated successfully!")
                else:
                    error_message = response_data.get('error', {}).get('message', 'An error occurred')
                    messages.error(request, f"Error: {error_message}")

            except Exception as e:
                if 'INVALID_LOGIN_CREDENTIALS' in str(e):
                    messages.error(request, "Current password does not match our records.")
                else:
                    print(f"Error during password update: {str(e)}")
                    messages.error(request, f"Error: {str(e)}") 
                    
    return render(request, 'Owner-Settings.html', context)


        




 
     

def ownerlogout(request):
    # Retrieve the email from session
    email = request.session.get('email')

    if email:
        # Generate the email key used in Firebase
        email_key = email.replace('.', '_').replace('@', '_at_')

        # Update active_status to offline
        db.child("owners").child(email_key).update({"active_status": "offline"})
        
        # Start counting offline time in a separate thread
        def track_time_logged_out():
            start_time = time.time()  # Track the logout time
            while True:
                elapsed_time = int(time.time() - start_time)  # Convert elapsed time to integer seconds
                db.child("owners").child(email_key).update({"timeLoggedOut": elapsed_time})

                # If 86400 seconds have passed, increment `daysLogin` by 1
                if elapsed_time >= 86400:
                    days_login = db.child("owners").child(email_key).child("daysLogin").get().val() or 0
                    db.child("owners").child(email_key).update({
                        "daysLogin": days_login + 1,
                        "timeLoggedOut": 0  # Reset for the next day
                    })
                    start_time = time.time()  # Reset start time for the next day
                time.sleep(1)  # Update every second

        # Run the thread to update timeLoggedOut continuously
        threading.Thread(target=track_time_logged_out, daemon=True).start()

        # Clear the session data
        request.session.flush()
        messages.success(request, "Logged out successfully.")
    else:
        messages.error(request, "No active session found.")

    return redirect('owner_login')  # Redirect to the login page after logout








#This is for Students 
MAX_ATTEMPTS = 5  # Maximum allowed attempts
DELAY_MULTIPLIER = 10  # Delay multiplier in seconds for each failed attempt
LOCK_TIME = 300  # Lock time in seconds (e.g., 5 minutes)

# Use a dictionary to track failed attempts and delays per email
login_attempts = {}

def generate_otp():
    otp = random.randint(100000, 999999)  # Generates a 6-digit OTP
    otp_hash = hashlib.sha256(str(otp).encode()).hexdigest()  # Hashes the OTP
    return otp, otp_hash

def send_otp_email(email, otp):
    subject = 'Your OTP for Account Verification - CTU-AC Accredited Boarding Houses'
    
    # HTML message for better presentation
    html_message = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}
            .card {{
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                max-width: 600px;
                margin: auto;
                overflow: hidden;
                padding: 20px;
            }}
            .header {{
                background-color: #007bff;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .content {{
                margin: 20px 0;
                font-size: 16px;
                line-height: 1.5;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 14px;
                color: #555;
            }}
            .otp {{
                font-size: 20px;
                font-weight: bold;
                color: #4CAF50;
                text-align: center;
            }}
            .logo {{
                width: 50%;
                height: auto;
                display: block;
                margin: 0 auto;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h2>Account Verification Required</h2>
            </div>
            <img src="https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2FCTU-logo-BH.png?alt=media&token=23bd87f5-9483-4c77-910b-a3d3838e07d9" alt="CTU Logo" class="logo">
            <div class="content">
                <p>Hello,</p>
                <p>Thank you for signing up for CTU-AC Accredited Boarding Houses. To complete your registration and verify your email address, please use the following One-Time Password (OTP):</p>
                <p class="otp">{otp}</p>
            </div>
            <div class="footer">
                <p>Best regards,</p>
                <p>The Datalink Team</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text message as a fallback option
    message = f"""
    Hello,

    Thank you for signing up for CTU-AC Accredited Boarding Houses. To complete your registration and verify your email address, please use the following One-Time Password (OTP):

    OTP: {otp}

    Best regards,
    The Datalink Team
    """


    from_email = settings.EMAIL_HOST_USER  # The email configured in settings
    recipient_list = [email]
    
    # Send email with HTML content
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        html_message=html_message  # HTML message for better formatting
    )







def student_login(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    email = ""  # Initialize email variable

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Initialize or update the dictionary for this email
        if email not in login_attempts:
            login_attempts[email] = {'failed_attempts': 0, 'delay': 0, 'locked_until': None}

        # Check if the email is currently locked
        if login_attempts[email]['locked_until'] and timezone.now() < login_attempts[email]['locked_until']:
            remaining_time = (login_attempts[email]['locked_until'] - timezone.now()).seconds
            send_lockout_email(email, remaining_time)  # Send lockout email
            messages.error(request, f"This account is temporarily locked. Please try again in {remaining_time // 60} minutes and {remaining_time % 60} seconds.")
            return render(request, 'StudentLOGIN.html', {'popup_message': True, 'remaining_time': remaining_time, 'email': email})

        failed_attempts = login_attempts[email]['failed_attempts']
        delay = login_attempts[email]['delay']

        # Introduce delay based on the current failed attempts
        if delay > 0:
            time.sleep(delay)

        try:
            # Authenticate user with Firebase
            user = auth_instance.sign_in_with_email_and_password(email, password)

            # Get user data from Firebase Realtime Database
            trimmed_email_key = email.replace('.', '_').replace('@', '_at_')
            user_data = db.child("students").child(trimmed_email_key).get().val()

            if user_data is None:
                messages.error(request, "User not found. Please check your email or sign up.")
                return render(request, 'StudentLOGIN.html', {'email': email})

            if user_data.get('role') == 'removed':
                messages.error(request, "Your account has been banned. To contact the administrator, click Report below.")
                return render(request, 'StudentLOGIN.html', {'email': email})

            if user_data.get('role') != 'student':
                messages.error(request, "Unauthorized access. This account is not allowed to login as a Student.")
                return render(request, 'StudentLOGIN.html', {'email': email})

            # Update active_status to online, reset timeLoggedOut to 0, and increment daysLogin
            db.child("students").child(trimmed_email_key).update({
                "active_status": "online",
                "timeLoggedOut": 0,
                "daysLogin": user_data.get("daysLogin", 0) + 1  # Increment login days
            })

            # Log IP and URL with identity
            log_ip_and_url(ip_address, current_url, "student/student_login/", user_email=email, user_status="online", user_role=user_data.get("role"))

            # Reset failed attempts on successful login
            login_attempts[email] = {'failed_attempts': 0, 'delay': 0, 'locked_until': None}

            # Store the user information in the session
            request.session['user_id'] = user['localId']
            request.session['email'] = email
            request.session['user_data'] = user_data
            request.session['active_status'] = "online"

            messages.success(request, "Login successful!")
            return redirect('studenthomepage')

        except Exception as e:
            failed_attempts += 1
            delay = failed_attempts * DELAY_MULTIPLIER
            login_attempts[email]['failed_attempts'] = failed_attempts
            login_attempts[email]['delay'] = delay

            if failed_attempts >= MAX_ATTEMPTS:
                lock_until = timezone.now() + timezone.timedelta(seconds=LOCK_TIME)
                login_attempts[email]['locked_until'] = lock_until
                login_attempts[email]['failed_attempts'] = 0
                messages.error(request, "Too many failed attempts. Please try again later.")
            else:
                messages.error(request, "Invalid email or password. Please try again!")

            return render(request, 'StudentLOGIN.html', {'email': email})

    # Log the IP address and URL without identity for GET requests
    log_ip_and_url(ip_address, current_url, "student/student_login/")

    return render(request, 'StudentLOGIN.html', {'email': email})







def student_forgotpassword(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/student_forgotpassword/")
    if request.method == 'POST':
        student_id = request.POST.get('studentId')
        email = request.POST.get('email')
        birthday = request.POST.get('birthday')
        
        # Transform the email to match how it's stored in Firebase
        email_key = email.replace('.', '_').replace('@', '_at_')
        
        # Fetch the user data from Firebase
        try:
            user_data = db.child("students").child(email_key).get()
            
            # Check if user exists
            if user_data.val() is None:
                error_message = "Student account not found."
                return render(request, 'student_forgotpassword.html', {'error_message': error_message})
            
            # Get user data
            user_data = user_data.val()
            
            # Check if student ID and birthday match
            if user_data.get('student_id') != student_id or user_data.get('birthday') != birthday:
                error_message = "Student account not found."
                return render(request, 'student_forgotpassword.html', {'error_message': error_message})
            
            # Send password reset email using Pyrebase
            auth_instance.send_password_reset_email(email)
            
            success_message = f"A password reset link has been sent to {email}."
            return render(request, 'student_forgotpassword.html', {'success_message': success_message})

        except Exception as e:
            error_message = f"An unexpected error occurred while processing your request. Please try again later. (Error: {str(e)})"
            return render(request, 'student_forgotpassword.html', {'error_message': error_message})

    return render(request, 'student_forgotpassword.html')






def send_lockout_email(email, remaining_time):
    subject = "Account Temporarily Locked Due to Failed Login Attempts"
    current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    minutes_remaining = remaining_time // 60
    seconds_remaining = remaining_time % 60
    
    message = f"""
    Dear User,

    We have detected multiple failed login attempts for your account. To ensure the security of your account, it has been temporarily locked.

    Current time: {current_time}
    Your account will be unlocked in approximately {minutes_remaining} minutes and {seconds_remaining} seconds.

    If you believe this is a mistake, please contact our support team. 
    ctuacaccreditedbh@gmail.com

    Thank you for your understanding and cooperation.

    Best regards,
    Datalink Team
    """
    
    send_mail(
        subject,
        message,
        'your-email@gmail.com',  # From email
        [email],  # To email
        fail_silently=False,
    )



def studentSignupFirststep(request): 
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/student_login/studentSignupFirststep/")

    if request.method == 'POST': 
        student_id = request.POST.get('student_id')   
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        gender = request.POST.get('gender')
        birthday = request.POST.get('birthday')  
        course = request.POST.get('course')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')

        # Check if student_id is provided
        if not student_id:
            messages.error(request, 'Student ID is required')
            return render(request, 'StudentSignUp-FirstStep.html')

        # Check if password and confirm password match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'StudentSignUp-FirstStep.html')

        # Check for duplicate student_id in Firebase Realtime Database
        existing_students = db.child("students").get()
        if existing_students.each():
            for student in existing_students.each():
                if student.val().get("student_id") == student_id:
                    messages.error(request, 'This Student ID already exists. Please use a different Student ID.')
                    return render(request, 'StudentSignUp-FirstStep.html')

        try:
            # Create user in Firebase Authentication
            user = auth_instance.create_user_with_email_and_password(email, password)
            otp, otp_hash = generate_otp()
            otp_expiry = int(time.time()) + 300

            # Default profile picture URL
            default_profile_img_url = "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4"

            # Get current date and time
            signup_time = datetime.now().strftime("%B %d, %Y %I:%M %p")

            # Save user data in Firebase Realtime Database
            user_data = {
                "student_id": student_id,
                "username": username,
                "phone": phone,
                "email": email,
                "address": address,
                "gender": gender,
                "course": course,
                "birthday": birthday,
                "status": "pending",
                "verification_code": otp_hash,
                "otp_expiry": otp_expiry,
                "profile_picture": default_profile_img_url,
                "active_status": "offline",
                "role": "student",
                "signup_time": signup_time,
                "accountStatus": "pending",
                "timeLoggedOut": 0,
                "daysLogin": 0
            }

            # Use email as the key, replacing special characters.
            email_key = email.replace('.', '_').replace('@', '_at_')

            # Save user data in Firebase Realtime Database
            db.child("students").child(email_key).set(user_data)

            # Send OTP to the user
            send_otp_email(email, otp)
            
            # Set session data
            request.session['user_data'] = {'email': email}

            messages.success(request, 'Account created successfully. Please verify your account.')
            return redirect('studentverify')

        except Exception as e:
            error_message = str(e)
            if "EMAIL_EXISTS" in error_message:
                messages.error(request, 'An account with this email already exists. Please use a different email.')
            else:
                messages.error(request, f'Error creating account: {error_message}')
    
    return render(request, 'StudentSignUp-FirstStep.html')






def studentSignupSecondstep(request):
    return render(request, 'StudentSignUp-SecondStep.html')

def studentProfilePicture(request):
    return render(request, 'Student-ProfilePictureStep.html')

def studentbase(request):
    # Retrieve user information from the session
    user_data = request.session.get('user_data')  # Assuming you stored user data in session
    username = user_data.get('username') if user_data else None

    # Pass the username to the context
    context = {
        'username': username,
        # ... other context data ...
    }
    return render(request, 'Student-base.html', context)



def get_student_context(request):
    # Retrieve user data from session
    user_data = request.session.get('user_data', {})
    email = user_data.get('email')  # Ensure email is in the session
    #greeting = get_greeting()
    # Check if email is present in the session
    if not email:
        messages.error(request, 'Email not found in session. Please log in again.')
        return None  # Indicate that the email was not found

    # Create email_key for Firebase key
    email_key = email.replace('.', '_').replace('@', '_at_')
    
    # Define default values
    days_login = 0

    try:
        # Fetch student data from Firebase
        student_data = db.child("students").child(email_key).get().val()
        if student_data:
            days_login = student_data.get('daysLogin', 0)
    except Exception as e:
        print(f"Error fetching student data: {e}")

    # Define the default profile picture URL
    default_profile_picture_url = (
        "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/"
        "default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4"
    )

    # Initialize fields with defaults
    active_status = "offline"
    course = ''
    gender = ''
    student_id = ''
    account_status = ''
    days_login = 0
    applied_room_status = ''
    boardinghouse_name = ''
    room_name = ''
    unseen_notifications_count = 0  # Initialize unseen notifications count

    try:
        # Get the student data from Firebase
        student_data = db.child("students").child(email_key).get().val()
        if student_data:
            active_status = student_data.get('active_status', 'offline')
            course = student_data.get('course', '')
            gender = student_data.get('gender', '')
            student_id = student_data.get('student_id', '')
            account_status = student_data.get('accountStatus', '')
            days_login = student_data.get('daysLogin', 0)
            applied_room_status = student_data.get('appliedRoomStatus', '')
            boardinghouse_name = student_data.get('boardinghouseName', '')
            room_name = student_data.get('roomName', '')

            # Fetch and count unseen notifications
            notifications = student_data.get('notifications', {})
            unseen_notifications_count = sum(
                1 for notif in notifications.values() if not notif.get('seen', False)
            )
    except Exception as e:
        print(f"Error fetching student data: {e}")

    # Prepare context for rendering
    context = {
        'email': email,
        'email_key': email_key,
        'username': user_data.get('username', 'Student'),
        'profile_picture': user_data.get('profile_picture', default_profile_picture_url),
        'default_profile_picture_url': default_profile_picture_url,
        'active_status': active_status,
        'course': course,
        'gender': gender,
        'student_id': student_id,
        'accountStatus': account_status,
        'daysLogin': days_login,
        'appliedRoomStatus': applied_room_status,  # Include appliedRoomStatus
        'boardinghouseName': boardinghouse_name,  # Include boardinghouseName
        'roomName': room_name,  # Include roomName
        'unseen_notifications_count': unseen_notifications_count,  # Include unseen notifications count
        'daysLogin': days_login,
        #'greeting': greeting,
    }

    return context



@csrf_exempt  # If CSRF token is manually handled in the script
def update_days_login(request):
    if request.method == 'POST':
        user_data = request.session.get('user_data', {})
        email = user_data.get('email')
        if not email:
            return JsonResponse({'error': 'Email not found in session'}, status=400)
        
        email_key = email.replace('.', '_').replace('@', '_at_')
        
        try:
            student_data = db.child("students").child(email_key).get().val()
            if student_data:
                db.child("students").child(email_key).update({'daysLogin': 2}) 
                messages.success(request, "Tour is done! Let's go apply rooms!")
                return JsonResponse({'message': 'daysLogin updated successfully'})
            else:
                return JsonResponse({'error': 'Student data not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



def studenthomepage(request):
    # Log IP address and URL
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studenthomepage/")

    context = get_student_context(request)
    context['active_page'] = 'home'

    if context is None:
        return redirect('student_login')

    # Fetch notifications for the student
    student_email = context.get('email')
    if student_email:
        email_key = student_email.replace('.', '_').replace('@', '_at_')
        notifications = db.child("students").child(email_key).child("notifications").get().val()

        if notifications:
            current_notification_count = len(notifications)
            last_notification_count = request.session.get('last_notification_count', 0)

            # Check if there are new notifications
            if current_notification_count > last_notification_count:
                messages.success(request, "You have new notifications.")
                request.session['last_notification_count'] = current_notification_count
        else:
            # Set last_notification_count to 0 if there are no notifications
            request.session['last_notification_count'] = 0

    # Fetch and prepare boarding house data with filters
    try:
        # Get selected filter from the request (GET or POST based on your form setup)
        selected_filter = request.GET.get('filter', 'all')  # Default to 'all' if no filter is selected
        selected_rating = request.GET.get('rating', None)

        # Fetch all entries under 'ownersBoardingHouse' and filter for approved boarding houses
        firebase_data = db.child('ownersBoardingHouse').get().val()
        approved_data = {}

        if firebase_data:
            for owner_key, owner_data in firebase_data.items():
                if owner_data.get('boardinghouseStatus') == 'approved':
                    if selected_filter != "all" and selected_filter:
                        # Apply filter based on typeOfRental
                        type_of_rental = owner_data.get('typeOfRental', [])
                        if selected_filter not in type_of_rental:
                            continue  # Skip this boarding house if it doesn't match the filter
                    
                    # Apply rating filter
                    if selected_rating:
                        ratings = owner_data.get('ratings', {})
                        average_rating = 0
                        if ratings:
                            total_rating = sum(rating['rating'] for rating in ratings.values())
                            average_rating = total_rating / len(ratings) if len(ratings) > 0 else 0
                        
                        # Handle different rating conditions
                        if selected_rating == "2_below" and average_rating > 2:
                            continue  # Skip if average rating is above 2
                        if selected_rating == "5" and average_rating < 5:
                            continue  # Skip if average rating is below 5
                        if selected_rating == "4" and average_rating < 4:
                            continue  # Skip if average rating is below 4
                        if selected_rating == "3" and average_rating < 3:
                            continue  # Skip if average rating is below 3
                        if selected_rating == "2" and average_rating < 2:
                            continue  # Skip if average rating is below 2

                    rooms = owner_data.get('rooms', [])
                    
                    # Extract prices and calculate highest and lowest
                    prices = [float(room['price']) for room in rooms if 'price' in room]
                    if prices:
                        min_price = min(prices)
                        max_price = max(prices)
                        owner_data['price_range'] = f"{min_price:.2f} - {max_price:.2f}"
                    else:
                        owner_data['price_range'] = "N/A"

                    # Calculate average rating and round it
                    ratings = owner_data.get('ratings', {})
                    if ratings:
                        total_rating = sum(rating['rating'] for rating in ratings.values())
                        average_rating = total_rating / len(ratings) if len(ratings) > 0 else 0
                        owner_data['average_rating'] = round(average_rating)
                    else:
                        owner_data['average_rating'] = 0

                    # Prepare star counts for template
                    owner_data['full_stars'] = owner_data['average_rating']
                    owner_data['empty_stars'] = 5 - owner_data['average_rating']

                    # Count available rooms excluding those with 'notShown' status
                    available_rooms_count = sum(
                        1 for room in rooms if room.get('availabilityStatus') == 'AVAILABLE' and room.get('status') != 'notShown'
                    )
                    if available_rooms_count > 0:
                        owner_data['available_rooms_message'] = f"{available_rooms_count} Rooms Available"
                    else:
                        owner_data['available_rooms_message'] = "No Rooms Available"

                    approved_data[owner_key] = owner_data

            context['approved_boardinghouses'] = approved_data
        else:
            context['approved_boardinghouses'] = {}

    except Exception as e:
        print(f"Error fetching boardinghouse data: {e}")
        context['approved_boardinghouses'] = {}

    # Pass the selected filter back to the template for highlighting the active filter
    context['selected_filter'] = selected_filter
    context['selected_rating'] = selected_rating

    # Render the homepage with context containing only approved boarding houses
    return render(request, 'Student-Homepage.html', context)









def student_homeReport(request):
    # Log IP address and URL for debugging or analytics purposes
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studenthomepage/student_report_problem")

    # Fetch context data for the logged-in student
    context = get_student_context(request)

    if context is None:  # Handle missing email in session
        messages.error(request, 'Email not found in session. Please log in again.')
        return redirect('student_login')

    # Extract the necessary details from the context
    email = context.get('email', '')
    username = context.get('username', '')

    # Include student details in the context for the template
    student_details = {
        'email': email,
        'username': username,
    }

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Format email key for Firebase query
        email_key = email.replace('.', '_').replace('@', '_at_')

        try:
            # Check if the email exists in the 'students' table in Firebase
            student_data = db.child("students").child(email_key).get()

            if student_data.val():
                # If email exists, proceed with saving the report
                date_of_report = datetime.now().strftime("%B %d, %Y %I:%M %p")

                report_data = {
                    "name": name,
                    "email": email,
                    "message": message,
                    "date_of_report": date_of_report,
                    "status": "unfixed"
                }

                # Save the report data under the email_key in messages
                db.child("usersReport").child("students").child(email_key).child("messages").push(report_data)
                messages.success(request, 'Your report has been sent. Please wait for the response.')
            else:
                # If email doesn't exist, show error
                messages.error(request, 'Only students with a registered account can report.')

        except Exception as e:
            error_message = str(e)
            print(f"Exception occurred: {error_message}")  # Debugging
            messages.error(request, f'Error processing your request: {error_message}')

        return redirect('student_homeReport')

    # Render the template with student details
    return render(request, 'student-homeReport.html', {**context, **student_details})








def student_apply_now(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/student_apply_now/")

    context = get_student_context(request)

    if context is None or 'email' not in context:
        return redirect('student_login')

    context['active_page'] = 'home'
    owner_email = request.POST.get('ownerEmail')
    email_key = owner_email.replace('.', '_').replace('@', '_at_')

    # Fetch the boarding house data
    boarding_house_data = db.child('ownersBoardingHouse').child(email_key).get().val()
    if boarding_house_data is None:
        context['error'] = 'No boarding house found for this email.'
        return render(request, 'student_apply_now.html', context)

    # Filter out rooms with `status` set to `notShown`
    filtered_rooms = []
    for room in boarding_house_data.get('rooms', []):
        if room.get('status') != 'notShown':
            filtered_rooms.append(room)

    context['boarding_house'] = {**boarding_house_data, 'rooms': filtered_rooms}


    context['owner_email'] = owner_email

    # Student email and key formatting
    student_email = context['email']
    student_email_key = student_email.replace('.', '_').replace('@', '_at_')

    applied_rooms = set()
    room_statuses = {}
    has_left_feedback = False

    # Check for student applications and feedback
    try:
        # Correct path to fetch student applications
        studentsapplied = db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').get().val()
        if studentsapplied:
            for key, application in studentsapplied.items():
                if application.get('email') == student_email:
                    room_name = application.get('roomName')
                    applied_rooms.add(room_name)
                    room_statuses[room_name] = application.get("status")  # Fetch the status
                    # Check if feedback was left
                    if application.get('rating') is not None:
                        has_left_feedback = True

        # Check if the student has already left feedback
        rating_entry = db.child('ownersBoardingHouse').child(email_key).child('ratings').child(student_email_key).get().val()
        if rating_entry:
            has_left_feedback = True

    except Exception as e:
        print(f"Error checking student applications: {e}")

    context['applied_rooms'] = applied_rooms
    context['has_left_feedback'] = has_left_feedback
    context['room_statuses'] = room_statuses  # This holds the status for each room

    # Handle form submission for applying/canceling applications
    if request.method == 'POST':
        room_name = request.POST.get('roomName')

        # Check the student's accountStatus before proceeding
        account_status = context.get('accountStatus')
        if account_status == 'pending':
            messages.error(request, "Pending account can't apply for rooms yet.")
            return render(request, 'student_apply_now.html', context)
        elif account_status == 'rejected':
            messages.error(request, "Rejected accounts cannot apply for rooms.")
            return render(request, 'student_apply_now.html', context)
        elif account_status == 'disabled':
            messages.error(request, "Disabled accounts cannot apply for rooms.")
            return render(request, 'student_apply_now.html', context)

        if room_name:
            if room_name in applied_rooms:
                # Cancel the application by checking status
                for key, application in studentsapplied.items():
                    if application.get('roomName') == room_name and application.get('email') == student_email:
                        current_status = application.get("status")
                        if current_status == "cancelled":
                            messages.error(request, "Your application has been cancelled; you cannot cancel it again.")
                        else:
                            # Toggle status between 'pending' and 'cancelled'
                            new_status = "cancelled" if current_status == "pending" else "pending"
                            db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_email_key).child(room_name).update({"status": new_status})
                            room_statuses[room_name] = new_status  # Update the room status
                            messages.success(request, f"Your application status for {room_name} has been updated to {new_status}.")
                        break
            else:
                # Check if the student is already approved in another boarding house
                appliedRoomStatus = db.child("students").child(student_email_key).child('appliedRoomStatus').get().val()

                if appliedRoomStatus == 'approved':
                    messages.error(request, "You can't apply to any rooms right now, you already have a room approved.")
                    return render(request, 'student_apply_now.html', context)

                # Fetch the availability status of the selected room
                selected_room = next((room for room in boarding_house_data.get('rooms', []) if room.get('roomName') == room_name), None)
                if selected_room and selected_room.get('availabilityStatus') == 'ROOM FULL':
                    messages.error(request, "The room you applied is already full.")
                    return render(request, 'student_apply_now.html', context)

                # If not already approved and the room is available, proceed with the application
                current_time = datetime.now().strftime("%B %d, %Y %I:%M %p")
                application_data = {
                    "boardinghouseName": boarding_house_data.get('boardinghouseName', ''),
                    "email": student_email,
                    "roomName": room_name,
                    "username": request.POST.get('studentUsername'),
                    "student_id": request.POST.get('studentID'),
                    "course": request.POST.get('studentCourse'),
                    "gender": request.POST.get('studentGender'),
                    "profile_picture": request.POST.get('studentProfilePicture'),
                    "coverPhoto": boarding_house_data.get('coverPhoto', ''),
                    "time_applied": current_time,
                    "status": "pending",
                    "boardinghouseOwnerEmail": owner_email
                }

                # Save application data to the correct path without UID
                db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_email_key).child(room_name).set(application_data)

                # Update applied rooms and room statuses
                applied_rooms.add(room_name)
                room_statuses[room_name] = "pending"  # Set the initial status to pending

                # Show a success message
                messages.success(request, f"Your application for {room_name} has been submitted and is pending approval.")

                # Render the context with updated information
                return render(request, 'student_apply_now.html', context)


        # Handle feedback rating
        rating = (
            request.POST.get('rating1') or
            request.POST.get('rating2') or
            request.POST.get('rating3') or
            request.POST.get('rating4') or
            request.POST.get('rating5')
        )

        if rating and not has_left_feedback:
            rating_data = {
                "email": student_email,
                "username": request.POST.get('username'),
                "student_id": request.POST.get('student_id'),
                "profile_picture": request.POST.get('profile_picture'),
                "rating": int(rating),
                "role": "student"
            }
            db.child('ownersBoardingHouse').child(email_key).child('ratings').child(student_email_key).set(rating_data)
            has_left_feedback = True
            messages.success(request, "Thank you for leaving a rating!")

    context['has_left_feedback'] = has_left_feedback
    context['room_is_pending'] = {room_name: (status == "pending") for room_name, status in room_statuses.items()}

    return render(request, 'student_apply_now.html', context)


def trackLocation(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studenthomepage/student_apply_now/trackLocation")

    # Retrieve the student context
    context = get_student_context(request)

    if context is None or 'email' not in context:
        return redirect('student_login')  # Redirect if email not found

    # Get owner_email from POST data
    owner_email = request.POST.get('ownerEmail')

    if not owner_email:
        return JsonResponse({"error": "Owner email is required."}, status=400)

    try:
        # Fetch the owner's location from the database
        owner_email_key = owner_email.replace('.', '_').replace('@', '_at_')
        owner_location_ref = db.child("user_locations").child(owner_email_key).child("details")
        owner_location = owner_location_ref.get().val()

        # Add owner's location to context
        context['owner_location'] = owner_location

    except Exception as e:
        context['error'] = str(e)

    return render(request, 'trackLocation.html', context)




 
def studentapplication(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studentapplication/")
    # Retrieve the student context
    context = get_student_context(request)

    if context is None or 'email' not in context:
        return redirect('student_login')  # Redirect if email not found

    # Set the active page
    context['active_page'] = 'application'

    # Get the student’s email
    student_email = context['email']
    student_email_key = student_email.replace('.', '_').replace('@', '_at_')

    # Initialize an empty list for applications
    context['applications'] = []

    # Process cancellation or removal request if POST request
    if request.method == "POST":
        action_type = request.POST.get("action_type", "")
        room_name = request.POST.get("roomName")
        owner_email = request.POST.get("ownerEmail")
        status = request.POST.get("status", "cancelled")  # Default status to cancelled if not provided
        reason = request.POST.get("reason", "")  # Reason for removal request

        if action_type == "request_removal":
            try:
                # Fetch the student data for the removal request
                student_data = db.child("students").child(student_email_key).get().val()

                if student_data:
                    # Extract necessary data from student_data
                    student_id = student_data.get("student_id")
                    student_email = student_data.get("email")
                    username = student_data.get("username")
                    profile_picture = student_data.get("profile_picture")
                    room_name = student_data.get("roomName")
                    boardinghouse_name = student_data.get("boardinghouseName")
                    # Get the current date for when the request is being made 
                    current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
                    
                    # Save the removal request data
                    removal_data = {
                        "removalReason": reason,  # Reason for removal
                        "roomName": room_name,  # Room Name
                        "boardinghouseName": boardinghouse_name,  # Boardinghouse Name
                        "profile_picture": profile_picture,  # Profile Picture
                        "student_id": student_id,  # Student ID
                        "email": student_email,  # Student ID
                        "username": username,  # Username
                        "status": "pending",  # Status for the request
                        "dateRequested": current_date  # Date when the request was made
                    }

                    # Save the removal request data in the ownersBoardingHouseRequest/{student_email_key} path
                    db.child("ownersBoardingHouseRequest").child(student_email_key).set(removal_data)

                    # Update the appliedRoomStatus to "request for removal is pending" in the students node
                    db.child("students").child(student_email_key).update({
                        "appliedRoomStatus": "request for removal is pending",
                        "removalReason": reason,  # Optionally store the reason
                    })

                    messages.success(request, 'Your request for removal is pending approval.')
                    return redirect('studentapplication')
                else:
                    messages.error(request, 'Student data not found in the database.')
            except Exception as e:
                print(f"Error processing removal request: {e}")
                messages.error(request, 'An error occurred while processing your request.')


        elif room_name and owner_email and status == "cancelled":
            email_key = owner_email.replace('.', '_').replace('@', '_at_')

            # Update the application status in Firebase
            try:
                # Fetch the studentsapplied for the specific owner and student
                studentsapplied = db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_email_key).get().val()

                if studentsapplied:
                    application_found = False
                    # Check if this application exists for the student
                    if room_name in studentsapplied:  # Check if this application exists
                        application_data = studentsapplied[room_name]
                        # Check if the email matches
                        if application_data.get('email') == student_email:
                            # Update the status to "cancelled"
                            db.child('ownersBoardingHouse').child(email_key).child('studentsapplied').child(student_email_key).child(room_name).update({'status': 'cancelled'})
                            application_found = True
                            messages.success(request, 'Application cancelled successfully.')
                        else:
                            messages.error(request, 'No matching application found for the provided room and student.')
                    else:
                        messages.error(request, 'No application found for the specified room name.')
                else:
                    messages.error(request, 'No applications found for the owner.')
            except Exception as e:
                print(f"Error cancelling application: {e}")
                messages.error(request, 'An error occurred while cancelling the application.')

        else:
            messages.error(request, 'Invalid room or owner information provided.')

    # Load applications to display
    try:
        owners_data = db.child('ownersBoardingHouse').get().val()
        if owners_data:
            for owner_key, owner_data in owners_data.items():
                studentsapplied = owner_data.get('studentsapplied', {})
                if studentsapplied:
                    # Check for applications belonging to the current student
                    if student_email_key in studentsapplied:
                        applications = studentsapplied[student_email_key]
                        if isinstance(applications, dict):  # Ensure applications is a dictionary
                            for application_key, application_data in applications.items():
                                if application_data.get('email') == student_email:
                                    # Retrieve boardinghouseOwnerEmail from the application data
                                    boardinghouse_owner_email = application_data.get('boardinghouseOwnerEmail', '')
                                    context['applications'].append({
                                        'boardinghouseName': application_data.get('boardinghouseName', ''),
                                        'roomName': application_data.get('roomName', ''),
                                        'username': application_data.get('username', ''),
                                        'student_id': application_data.get('student_id', ''),
                                        'course': application_data.get('course', ''),
                                        'gender': application_data.get('gender', ''),
                                        'profile_picture': application_data.get('profile_picture', ''),
                                        'coverPhoto': application_data.get('coverPhoto', ''),
                                        'time_applied': application_data.get('time_applied', ''),  # Ensure this is in a sortable format
                                        'status': application_data.get('status', 'unknown'),
                                        'boardinghouseOwnerEmail': boardinghouse_owner_email or '',  # Safely assign the email
                                    })

        # Sort applications by time_applied (descending)
        context['applications'].sort(key=lambda x: x['time_applied'], reverse=True)

    except Exception as e:
        print(f"Error loading applications: {e}")
        context['applications'] = []

    return render(request, 'Student-Application.html', context)









    

# def studentmessage(request):
#     context = get_student_context(request)

#     if context is None:  # Check if email was not found
#         return redirect('student_login')  # Redirect to login page if email not found

#     context['active_page'] = 'messages'  # Set active page
#     return render(request, 'Student-Message.html', context)



def studentnotification(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studentnotification/")
    context = get_student_context(request)

    if context is None:
        return redirect('student_login')

    # Retrieve the student's email and get notifications from Firebase
    student_email = context.get('email')
    if student_email:
        email_key = student_email.replace('.', '_').replace('@', '_at_')

        # Handle notification deletion
        if request.method == "POST" and 'notification_id' in request.POST:
            notification_id = request.POST['notification_id']
            try:
                db.child("students").child(email_key).child("notifications").child(notification_id).remove()
                messages.success(request, "Notification removed successfully.")
            except Exception as e:
                messages.error(request, f"Error removing notification: {str(e)}")

        try:
            # Fetch notifications and mark them as seen
            notifications = db.child("students").child(email_key).child("notifications").get().val()
            if notifications:
                context['notifications'] = []

                # Iterate over notifications and mark unseen ones as seen
                for notif_key, notif_data in notifications.items():
                    seen = notif_data.get("seen", False)

                    # Add notification data to context
                    context['notifications'].append({
                        "id": notif_key,
                        "message": notif_data.get("message"),
                        "time_of_notification": notif_data.get("time_of_notification"),
                        "seen": seen
                    })

                    # If the notification is new (unseen), mark it as seen in Firebase
                    if not seen:
                        db.child("students").child(email_key).child("notifications").child(notif_key).update({"seen": True})

                # Sort notifications by `time_of_notification` in descending order
                context['notifications'].sort(
                    key=lambda x: datetime.strptime(x['time_of_notification'], "%B %d, %Y %I:%M %p"),
                    reverse=True
                )
            else:
                context['notifications'] = []

        except Exception as e:
            context['notifications'] = []
            print(f"Error fetching notifications: {str(e)}")

    context['active_page'] = 'notification'
    return render(request, 'Student-Notification.html', context)






def studentsettings(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studentsettings/")
    # Get student context
    context = get_student_context(request)

    if context is None:
        return redirect('student_login')  # Redirect to login page if email not found

    context['active_page'] = 'settings'  # Set active page

    if request.method == 'GET':
        # Fetch student data from Firebase
        email = context.get('email')
        trimmed_email_key = email.replace('.', '_').replace('@', '_at_')  # Consistent email key generation
        student_data = db.child("students").child(trimmed_email_key).get().val()

        if student_data:
            # Retrieve only the specified fields
            context['username'] = student_data.get('username', '')
            context['address'] = student_data.get('address', '')
            context['gender'] = student_data.get('gender', '')
            context['phone'] = student_data.get('phone', '')
            context['birthday'] = student_data.get('birthday', '')
            context['course'] = student_data.get('course', '')
            context['profile_picture'] = student_data.get('profile_picture', '')
            context['student_id'] = student_data.get('student_id', '')

        return render(request, 'Student-Settings.html', context)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'star_rating_update':
            # Handle star rating update
            star_rating = request.POST.get('star_rating')
            try:
                # Validate the star rating (should be between 1 and 5)
                if not star_rating or not star_rating.isdigit() or not 1 <= int(star_rating) <= 5:
                    messages.error(request, "Please select a valid star rating.")
                    return redirect('studentsettings')

                email = context.get('email')
                user_id = email.replace('.', '_').replace('@', '_at_')  # Consistent email key generation

                # Fetch the existing feedback for the user
                existing_feedback = db.child('usersReport').child('saofeedback').child('students').child(user_id).get()

                # Check if feedback already exists
                if existing_feedback.val() and 'star_rating' in existing_feedback.val():
                    messages.error(request, "You have already submitted feedback.")
                    return redirect('studentsettings')

                # Fetch additional user information
                student_data = db.child('students').child(user_id).get().val()  # Get student's data
                if student_data:
                    # Prepare the data to be saved
                    username = student_data.get('username', '')  # Assuming 'username' is stored in the database
                    role = student_data.get('role', '')  # Assuming 'role' is stored in the database
                    profile_picture = student_data.get('profile_picture', '')  # Assuming 'profile_picture' is stored

                    # Save the star rating and additional data in Firebase
                    db.child('usersReport').child('saofeedback').child('students').child(user_id).update({
                        'star_rating': int(star_rating),
                        'name': username,          # Save the username in the 'name' field
                        'email': email,            # Save the email
                        'role': role,              # Save the role
                        'profile_picture': profile_picture  # Save the profile picture URL
                    })

                    # Mark feedback as submitted
                    context['feedback_submitted'] = True
                    messages.success(request, f"Star rating updated to {star_rating} stars!")

                else:
                    messages.error(request, "Student data not found.")
                    return redirect('studentsettings')

            except Exception as e:
                messages.error(request, f"Error saving star rating: {str(e)}")
                return redirect('studentsettings')



        if form_type == 'profile_update':
            # Handle profile update
            username = request.POST.get('username')
            address = request.POST.get('address')
            gender = request.POST.get('gender')
            phone = request.POST.get('phone')
            birthday = request.POST.get('birthday')
            course = request.POST.get('course')

            # Handle profile picture upload
            profile_picture = request.FILES.get('profile_picture')

            # Validation
            if not username or not address or not phone or not birthday:
                messages.error(request, "All required fields must be filled.")
                return redirect('studentsettings')

            # Validate phone number (e.g., ensure it starts with +639)
            if not phone.startswith('+639') or len(phone) != 13:
                messages.error(request, "Phone number must start with +639 and be 11 digits in total.")
                return redirect('studentsettings')

            # Validate birthday (e.g., between 1900 and 2010)
            try:
                birthday_year = int(birthday.split('-')[0])
                if birthday_year < 1900 or birthday_year > 2010:
                    messages.error(request, "Birthday must be between 1900 and 2010.")
                    return redirect('studentsettings')
            except ValueError:
                messages.error(request, "Invalid birthday format.")
                return redirect('studentsettings')

            try:
                email = context.get('email')
                trimmed_email_key = email.replace('.', '_').replace('@', '_at_')  # Consistent email key

                # Default profile picture URL
                default_profile_img_url = "https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4"

                # Handle profile picture upload if a new file was provided
                if profile_picture:
                    profile_picture_name = profile_picture.name
                    profile_picture_path = f'students_profilepicture/{trimmed_email_key}/{profile_picture_name}'
                    storage.child(profile_picture_path).put(profile_picture)
                    profile_picture_url = storage.child(profile_picture_path).get_url(None)
                else:
                    profile_picture_url = context.get('profile_picture', default_profile_img_url)

                # Prepare updated data
                updated_data = {
                    "username": username,
                    "address": address,
                    "gender": gender,
                    "phone": phone,
                    "birthday": birthday,
                    "course": course,
                    "profile_picture": profile_picture_url
                }

                # Update Firebase with new data
                db.child("students").child(trimmed_email_key).update(updated_data)

                # --- Notification Logic ---
                # Add a notification under the student's data
                notifications = db.child("students").child(trimmed_email_key).child("notifications").get().val() or {}
                notification_count = len(notifications) + 1

                # Create the notification message
                notification_message = (
                    f"Your profile has been successfully updated. Check the new details and contact support if needed."
                )

                # Format the current date and time
                time_of_notification = datetime.now().strftime("%B %d, %Y %I:%M %p")

                # Add new notification with both message and timestamp
                db.child("students").child(trimmed_email_key).child("notifications").child(f"notification{notification_count}").set({
                    "message": notification_message,
                    "time_of_notification": time_of_notification
                })

                # Fetch updated data to refresh the page
                student_data = db.child("students").child(trimmed_email_key).get().val()
                user_data = request.session.get('user_data', {})
                user_data.update(updated_data)
                request.session['user_data'] = user_data  # Save updated session data
                if student_data:
                    messages.success(request, "Profile updated successfully!")
                    context.update(student_data)
                    return redirect('studentsettings')
                else:
                    messages.error(request, "Error updating profile.")
                    return redirect('studentsettings')

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
                return redirect('studentsettings')
 
        elif form_type == 'password_update':
            current_password = request.POST.get('currentPassword')
            new_password = request.POST.get('newPassword')
            confirm_password = request.POST.get('confirmPassword')
            email = context.get('email')  # Assuming you have the email in context

            # Validate inputs
            if not current_password or not new_password or not confirm_password:
                messages.error(request, "All password fields are required.")
                return render(request, 'Student-Settings.html', context)

            if new_password != confirm_password:
                messages.error(request, "New password and confirm password do not match.")
                return render(request, 'Student-Settings.html', context)

            try:
                # Re-authenticate the user
                user = auth_instance.sign_in_with_email_and_password(email, current_password)
                id_token = user['idToken']

                # Use Firebase REST API to update the password
                firebase_api_key = "AIzaSyAfCuib-Q7FmAlr9oj9CIwBONeMkWnpdgU"  # Replace with your actual Firebase API key
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={firebase_api_key}"

                data = {
                    'idToken': id_token,
                    'password': new_password,
                    'returnSecureToken': True
                }

                # Make the API request to update the password
                response = requests.post(url, json=data)
                response_data = response.json()

                if response.status_code == 200:
                    messages.success(request, "Password updated successfully!")

                    # --- Notification Logic ---
                    # Add a notification under the student's data
                    email_key = email.replace('.', '_').replace('@', '_at_')  # Consistent email key
                    notifications = db.child("students").child(email_key).child("notifications").get().val() or {}
                    notification_count = len(notifications) + 1

                    # Create the notification message
                    notification_message = (
                        f"Your password has been successfully updated. If you didn't request this change, contact support immediately."
                    )

                    # Format the current date and time
                    time_of_notification = datetime.now().strftime("%B %d, %Y %I:%M %p")

                    # Add new notification with both message and timestamp
                    db.child("students").child(email_key).child("notifications").child(f"notification{notification_count}").set({
                        "message": notification_message,
                        "time_of_notification": time_of_notification
                    })

                else:
                    error_message = response_data.get('error', {}).get('message', 'An error occurred')
                    messages.error(request, f"Error: {error_message}")

            except Exception as e:
                if 'INVALID_LOGIN_CREDENTIALS' in str(e):
                    messages.error(request, "Current password does not match our records.")
                else:
                    print(f"Error during password update: {str(e)}")
                    messages.error(request, f"Error: {str(e)}")

     
    return render(request, 'Student-Settings.html', context)








def vigenere_encrypt(message, key):
    encrypted_message = []
    key = key.upper()
    key_length = len(key)
    key_index = 0

    for char in message:
        if char.isalpha():  # Encrypt only alphabetic characters
            shift = ord(key[key_index]) - ord('A')
            key_index = (key_index + 1) % key_length

            if char.isupper():
                encrypted_message.append(chr((ord(char) - ord('A') + shift) % 26 + ord('A')))
            else:
                encrypted_message.append(chr((ord(char) - ord('a') + shift) % 26 + ord('a')))
        else:
            encrypted_message.append(char)  # Non-alphabetic characters are not encrypted

    return ''.join(encrypted_message)

def vigenere_encrypt(message, key):
    encrypted_message = []
    key = key.upper()
    key_length = len(key)
    key_index = 0

    for char in message:
        if char.isalpha():  # Encrypt only alphabetic characters
            shift = ord(key[key_index]) - ord('A')
            key_index = (key_index + 1) % key_length

            if char.isupper():
                encrypted_message.append(chr((ord(char) - ord('A') + shift) % 26 + ord('A')))
            else:
                encrypted_message.append(chr((ord(char) - ord('a') + shift) % 26 + ord('a')))
        else:
            encrypted_message.append(char)  # Non-alphabetic characters are not encrypted

    return ''.join(encrypted_message)

def vigenere_decrypt(encrypted_message, key):
    decrypted_message = []
    key = key.upper()
    key_length = len(key)
    key_index = 0

    for char in encrypted_message:
        if char.isalpha():  # Decrypt only alphabetic characters
            shift = ord(key[key_index]) - ord('A')
            key_index = (key_index + 1) % key_length

            if char.isupper():
                decrypted_message.append(chr((ord(char) - ord('A') - shift + 26) % 26 + ord('A')))
            else:
                decrypted_message.append(chr((ord(char) - ord('a') - shift + 26) % 26 + ord('a')))
        else:
            decrypted_message.append(char)  # Non-alphabetic characters are not decrypted

    return ''.join(decrypted_message)



def sanitize_path_part(path_part):
    # Replace spaces with underscores and remove invalid characters
    return re.sub(r'[^a-zA-Z0-9_]', '', path_part.replace(' ', '_'))


def delete_conversation_by_owner(request, owner_email):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studenthomepage/owner_message/delete_conversation_by_owner/")

    # Fetch student context
    student_context = get_student_context(request)
    if student_context is None:  # User is not logged in
        return redirect('student_login')

    # Sanitize paths for secure Firebase key usage
    sanitized_from_student = sanitize_path_part(student_context['email'])  # Use the student's email
    sanitized_owner_email = sanitize_path_part(owner_email)

    # Construct the message path in Firebase for the student's messages
    path_1 = f'messages/{sanitized_from_student}-{sanitized_owner_email}'
    # path_2 is for the owner's messages to the student, which we will NOT delete
    path_2 = f'messages/{sanitized_owner_email}-{sanitized_from_student}'

    # Check and delete only the student's messages (path_1)
    messages_deleted = False
    messages_data = db.child(path_1).get()
    if messages_data.val() is not None:
        db.child(path_1).remove()
        messages_deleted = True
        print(f"Student's messages deleted successfully from: {path_1}")

    if not messages_deleted:
        print(f"No student's messages found for deletion at path: {path_1}")

    # Redirect back to the conversation with the owner
    return redirect(f'/student/studenthomepage/owner_message?owner_email={owner_email}')




# Function to handle messaging for owners
def owner_message(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studenthomepage/owner_message/")
    # Fetch student context (for example, from session or logged-in user)
    student_context = get_student_context(request)
    if student_context is None:  # User is not logged in
        return redirect('student_login')

    # Fetch owners data from the database
    owners_data = db.child('owners').get()
    owner_list = []

    if owners_data and owners_data.each():
        for item in owners_data.each():
            owner_email_key = item.key()
            owner_info = {
                'firstname': item.val().get('firstname', 'No Firstname'),
                'lastname': item.val().get('lastname', 'No Lastname'),
                'email': item.val().get('email', 'No Email'),
                'activeStatus': item.val().get('active_status', 'offline'),
                'profileImage': item.val().get('profile_picture', 'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4'),
            }

            # Fetch associated boarding house for the owner
            boarding_house_data = db.child('ownersBoardingHouse').child(owner_email_key).get()
            owner_info['boardinghouseName'] = boarding_house_data.val().get('boardinghouseName', 'No Boarding House') if boarding_house_data and boarding_house_data.val() else 'No Boarding House'

            owner_list.append(owner_info)

    # Determine which owner is selected based on the query parameter 'owner_email'
    current_owner_email = request.GET.get('owner_email')
    selected_owner = None
    if current_owner_email:
        selected_owner = next((owner for owner in owner_list if owner['email'] == current_owner_email), None)

    # Handle AJAX request for fetching messages
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        sanitized_from_student = sanitize_path_part(student_context['email'])
        sanitized_current_owner_email = sanitize_path_part(current_owner_email)

        path_1 = f'messages/{sanitized_from_student}-{sanitized_current_owner_email}'
        path_2 = f'messages/{sanitized_current_owner_email}-{sanitized_from_student}'

        messages = []

        for path in [path_1, path_2]:
            messages_data = db.child(path).get()
            if messages_data and messages_data.each():
                for msg in messages_data.each():
                    message_data = msg.val()
                    decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                    messages.append({
                        'from': message_data['from'],
                        'message': decrypted_message,
                        'timestamp': message_data['timestamp']
                    })

        # Sort messages by timestamp
        messages.sort(key=lambda msg: datetime.strptime(msg['timestamp'], '%B %d, %Y %I:%M %p'))

        return JsonResponse({'messages': messages})

    # Handle message sending
    if request.method == 'POST':
        if 'delete' in request.POST:  # Handle delete functionality
            current_owner_email = request.POST.get('owner_email')

            # Debugging: Check if current_student_email is being passed
            print(f"Received owner_email: {current_owner_email}")

            # Ensure student_email is not None
            if not current_owner_email:
                print("Error: owner_email is None.")
                return redirect('owner_message')

            # Call the delete function
            delete_conversation_by_owner(request, current_owner_email)

            # Redirect back to the conversation page
            return redirect(f'{request.path}?owner_email={current_owner_email}')

        else:  # Handle sending messages to owner
            message = request.POST.get('message')
            from_student = student_context['email']  # Get student email from the student context
            to_owner = request.POST.get('to_owner_email')

            # Sanitize the email parts
            sanitized_from_student = sanitize_path_part(from_student) if from_student else None
            sanitized_to_owner = sanitize_path_part(to_owner) if to_owner else None

            if not sanitized_from_student or not sanitized_to_owner:
                print(f"Error: Sanitized path parts are None. from_student: {sanitized_from_student}, to_owner: {sanitized_to_owner}")
                return redirect('student_message')

            # Encrypt the message
            encrypted_message = vigenere_encrypt(message, 'DATALINK')
            message_uid = str(uuid4())

            # Save the message to the database
            message_data = {
                'from': from_student,
                'to': to_owner,
                'message': encrypted_message,
                'timestamp': datetime.now().strftime('%B %d, %Y %I:%M %p')  # Format the date and time
            }

            message_path = f'messages/{sanitized_from_student}-{sanitized_to_owner}/{message_uid}'
            db.child(message_path).set(message_data)

            # Redirect after sending the message
            return redirect(f'{request.path}?owner_email={to_owner}')

    # Fetch messages for the selected owner
    messages = []
    if current_owner_email:
        sanitized_from_student = sanitize_path_part(student_context['email'])
        sanitized_current_owner_email = sanitize_path_part(current_owner_email)

        # Define path_1 and path_2
        path_1 = f'messages/{sanitized_from_student}-{sanitized_current_owner_email}'
        path_2 = f'messages/{sanitized_current_owner_email}-{sanitized_from_student}'

        # Fetch messages from both paths
        for path in [path_1, path_2]:
            messages_data = db.child(path).get()
            if messages_data and messages_data.each():
                for msg in messages_data.each():
                    message_data = msg.val()
                    decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                    messages.append({
                        'from': message_data['from'],
                        'message': decrypted_message,
                        'timestamp': message_data['timestamp']
                    })

    # Sort messages by timestamp
    messages.sort(key=lambda msg: msg['timestamp'], reverse=False)

    # Show modal if messages limit is reached
    show_modal = len(messages) >= 15

    # Prepare the context for rendering
    context = {
        'selected_owner': selected_owner,
        'owner_list': owner_list,  # Include owners in the context
        'messages': messages,
        'current_owner_email': current_owner_email,
        'show_modal': show_modal,  # Flag for showing the modal
        **student_context,  # Include student context in the final context
        'student_context': student_context,
    }

    # Use the render function to return an HTTP response with the context
    return render(request, 'message-student-owners.html', context)






def delete_conversation(request, superadmin_email):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studenthomepage/delete_conversation")
    
    student_context = get_student_context(request)
    if student_context is None:  # User is not logged in
        return redirect('student_login')

    sanitized_from_student = sanitize_path_part(student_context['email'])
    sanitized_superadmin_email = sanitize_path_part(superadmin_email)

    messages_path = f'messages/{sanitized_from_student}-{sanitized_superadmin_email}'

    # Delete messages if they exist
    messages_data = db.child(messages_path).get()
    if messages_data.val() is not None:
        db.child(messages_path).remove()
        print(f"Messages deleted successfully from: {messages_path}")
    else:
        print(f"No messages found for deletion at path: {messages_path}")

    # Redirect back to the same conversation with the query parameter
    return redirect(f'/student/studenthomepage/student_message?superadmin_email={superadmin_email}')


def student_message(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/studenthomepage/student_message")

    student_context = get_student_context(request)
    if student_context is None:  # User is not logged in
        return redirect('student_login')

    # Fetch superadmins
    superadmin_data = db.child('saoaccounts').child('datas').child('superadmin').get()
    superadmin_list = []

    if superadmin_data and superadmin_data.each():
        for item in superadmin_data.each():
            uid = item.key()
            superadmin_info = {
                'name': item.val().get('name', 'No Name'),
                'email': item.val().get('email', 'No Email'),
                'profileImage': item.val().get('profileImage', 'https://firebasestorage.googleapis.com/v0/b/ctuacaccreditedboardinghouse.appspot.com/o/default_profileimg%2Fprofile-default.png?alt=media&token=aef7b39e-480c-4f18-989a-fc13c5f242f4'),
                'activeStatus': item.val().get('active_status', 'offline')
            }
            if uid.startswith('superadmin'):
                superadmin_list.append(superadmin_info)

    if request.method == 'POST':
        if 'delete' in request.POST:  # Handle delete functionality
            current_superadmin_email = request.POST.get('superadmin_email')

            if not current_superadmin_email:
                return redirect('student_message')

            # Call the delete function
            delete_conversation(request, current_superadmin_email)

            # Redirect back to the conversation page
            return redirect(f'{request.path}?superadmin_email={current_superadmin_email}')
        else:  # Handle sending messages
            message = request.POST.get('message')
            from_student = student_context['email']
            to_superadmin = request.POST.get('to_superadmin_email')

            if not from_student or not to_superadmin:
                return redirect('student_message')

            sanitized_from_student = sanitize_path_part(from_student)
            sanitized_to_superadmin = sanitize_path_part(to_superadmin)

            encrypted_message = vigenere_encrypt(message, 'DATALINK')
            message_uid = str(uuid4())

            message_data = {
                'from': from_student,
                'to': to_superadmin,
                'message': encrypted_message,
                'timestamp': datetime.now().strftime('%B %d, %Y %I:%M %p')
            }

            message_path = f'messages/{sanitized_from_student}-{sanitized_to_superadmin}/{message_uid}'
            db.child(message_path).set(message_data)

            # After sending the message, reload the page
            return redirect(f'{request.path}?superadmin_email={to_superadmin}')

    # Initialize sanitized_from_student early to avoid unbound variable error
    sanitized_from_student = None

    # Fetch messages for the student-superadmin conversation
    messages = []
    current_superadmin_email = request.GET.get('superadmin_email')

    if current_superadmin_email:
        sanitized_from_student = sanitize_path_part(student_context['email'])
        sanitized_current_superadmin_email = sanitize_path_part(current_superadmin_email)

        path_1 = f'messages/{sanitized_from_student}-{sanitized_current_superadmin_email}'
        path_2 = f'messages/{sanitized_current_superadmin_email}-{sanitized_from_student}'

        for path in [path_1, path_2]:
            messages_data = db.child(path).get()
            if messages_data and messages_data.each():
                for msg in messages_data.each():
                    message_data = msg.val()
                    decrypted_message = vigenere_decrypt(message_data['message'], 'DATALINK')
                    messages.append({
                        'from': message_data['from'],
                        'message': decrypted_message,
                        'timestamp': message_data['timestamp']
                    })

    selected_superadmin = next((superadmin for superadmin in superadmin_list if superadmin['email'] == current_superadmin_email), None)
    messages.sort(key=lambda msg: msg['timestamp'], reverse=False)

    # Track the current number of messages
    previous_message_count = len(messages)

    # If the request is an AJAX request, return the messages without reloading the page
    if request.is_ajax():
        return JsonResponse({'messages': messages})

    # Show modal if messages limit is reached
    show_modal = len(messages) >= 15

    context = {
        'selected_superadmin': selected_superadmin,
        'superadmin_list': superadmin_list,
        'messages': messages,
        'current_superadmin_email': current_superadmin_email,
        'show_modal': show_modal,
        **student_context,
    }

    return render(request, 'message-student.html', context)


















# class SendMessageView(View):
#     def post(self, request):
#         data = json.loads(request.body)
#         superadmin_email = data['superadmin_email']  # Email of the superadmin
#         user_email = data['user_email']  # Email of the user sending the message
#         message = data['message']  # The message to be sent

#         # Create a unique chat identifier
#         chat_id = f"{superadmin_email.replace('.', '_')}_{user_email.replace('.', '_')}"

#         # Push the message to Firebase
#         messages_ref = db.reference(f'chats/studentchats/{chat_id}')
#         message_id = messages_ref.push({
#             'message': message,
#             'timestamp': timezone.now().isoformat()
#         }).key

#         return JsonResponse({'status': 'success', 'message_id': message_id})

# class GetMessagesView(View):
#     def get(self, request, superadmin_email, user_email):
#         # Create a unique chat identifier
#         chat_id = f"{superadmin_email.replace('.', '_')}_{user_email.replace('.', '_')}"

#         # Get messages from Firebase
#         messages_ref = db.reference(f'chats/studentchats/{chat_id}')
#         messages = messages_ref.get() or {}

#         # Prepare messages for response
#         formatted_messages = [{
#             'message_id': message_id,
#             'message': msg['message'],
#             'timestamp': msg['timestamp']
#         } for message_id, msg in messages.items()]

#         return JsonResponse({'status': 'success', 'messages': formatted_messages})

def studentlogout(request):
    email = request.session.get('email')
    if email:
        email_key = email.replace('.', '_').replace('@', '_at_')
        
        # Update active_status to offline in the students table
        db.child("students").child(email_key).update({"active_status": "offline"})
        
        # Start counting offline time in a separate thread
        def track_time_logged_out():
            start_time = time.time()  # Track the logout time
            while True:
                elapsed_time = int(time.time() - start_time)  # Convert elapsed time to integer seconds
                db.child("students").child(email_key).update({"timeLoggedOut": elapsed_time})
                
                # If 86400 seconds have passed, increment `daysLogin` by 1
                if elapsed_time >= 86400:
                    days_login = db.child("students").child(email_key).child("daysLogin").get().val()
                    db.child("students").child(email_key).update({
                        "daysLogin": days_login + 1,
                        "timeLoggedOut": 0  # Reset for the next day
                    })
                    start_time = time.time()  # Reset start time for the next day
                time.sleep(1)  # Update every second

        # Run the thread to update timeLoggedOut continuously
        threading.Thread(target=track_time_logged_out, daemon=True).start()

    request.session.flush()  # Clear the session
    messages.success(request, "You have been logged out successfully.")
    return redirect('student_login')



 
def verify_otp(email, input_otp): 
    try:
        # Fetch student data based on email
        student_data = db.child("students").order_by_child("email").equal_to(email).get()

        # Check if student_data is valid
        if not student_data.each():  # Check if the data is empty
            return False, "User data not found."

        # Get the first user's data
        user_data = student_data.each()[0].val()  # Get the first item

        if int(time.time()) > user_data['otp_expiry']:
            return False, "The OTP has expired. Please request a new one."

        otp_hash = user_data.get('verification_code')
        input_otp_hash = hashlib.sha256(str(input_otp).encode()).hexdigest()

        if otp_hash == input_otp_hash:
            # Use the key from the first item to update
            user_id = student_data.each()[0].key()  # Get the key for the user
            db.child("students").child(user_id).update({"status": "verified"})
            return True, "OTP verified successfully."
        else:
            return False, "Invalid OTP. Please try again."
    except Exception as e:
        return False, f"Error verifying OTP: {str(e)}"




def studentverify(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    current_url = request.path
    log_ip_and_url(ip_address, current_url, "student/student_login/studentSignupFirststep/studentverify/")
    if request.method == 'POST':
        email = request.session.get('user_data', {}).get('email')
        if not email:
            messages.error(request, "Session expired. Please create an account again.")
            return redirect('studentSignupFirststep')

        input_otp = request.POST.get('otp')
        action = request.POST.get('action')

        if action == 'verify':
            is_valid, message = verify_otp(email, input_otp)
            if is_valid:
                messages.success(request, message)
                return redirect('student_login')
            else:
                messages.error(request, message)

        elif action == 'resend':
            try:
                otp, otp_hash = generate_otp()
                otp_expiry = int(time.time()) + 300
                user_data = db.child("students").child(email).get().val()
                if user_data:
                    db.child("students").child(email).update({"verification_code": otp_hash, "otp_expiry": otp_expiry})
                    send_otp_email(email, otp)
                    messages.success(request, 'OTP resent successfully. Please check your email.')
                else:
                    messages.error(request, "No user data found to resend OTP.")
            except Exception as e:
                messages.error(request, f"Error resending OTP: {str(e)}")

    return render(request, 'student_verify.html')


     

