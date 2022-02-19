from itertools import starmap
import re
from .google import *
import requests
from django.shortcuts import render, redirect
from .decorators import *
from django.http import HttpResponse , HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from allauth.account.views import SignupView, LoginView
from .models import *
import logging
from datetime import datetime
import time
from django.contrib.auth import logout
from hurry.filesize import size
import os.path
from mimetypes import MimeTypes
import pytz
import random,string,secrets
from datetime import date, datetime, time, timedelta
import operator

#google api
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from allauth.socialaccount.models import SocialToken, SocialApp


def create_calendar(user):
    current_user = user
    current_student = Student.objects.get(user=current_user)

    calendar = {
    'summary': 'Uth Groups',
    'timeZone': 'Europe/Athens'
    }
    service = google_service(current_user,"calendar")
    created_calendar = service.calendars().insert(body=calendar).execute()
    if created_calendar == None:
        return None
    return created_calendar['id']


def create_event(user,meeting_details):
    #set start and end time
    local_timezone = pytz.timezone('Europe/Athens')
    if (meeting_details['start'] == "now") and (meeting_details['end'] == "now"):
        start = datetime.now(local_timezone)
        end = start
    else:
        start = meeting_details['start']
        end = meeting_details['end']
    
    #find attendess course or group and create google meet id
    attendees = []
    course = None
    group = None
    res = ''.join(secrets.choice(string.ascii_letters + string.digits) for x in range(20))

    if meeting_details['group_id'] == None:
        course = Course.objects.get(pk=meeting_details['course_id'])
        current_user = course.owner.user
        current_student = Student.objects.get(user=current_user)
        service = google_service(current_user,"calendar")
        attendees_local_db = course.participants.all()
        for member in course.participants.all():
            attendee = {'email': member.user.email}
            attendees.append(attendee)
        #if the event is created from an admin and not the owner
        if current_student != course.owner:
            attendee = {'email': course.owner.user.email}
            attendees.append(attendee)
        code = str(res) + "_" + "course_" + str(course.pk)
    else:
        group = Group.objects.get(pk=meeting_details['group_id'])
        current_user = group.owner.user
        current_student = Student.objects.get(user=current_user)
        service = google_service(current_user,"calendar")
        attendees_local_db = group.participants.all()
        for member in group.participants.all():
            attendee = {'email': member.user.email}
            attendees.append(attendee)
        #if the event is created from an admin and not the owner
        if current_student != group.owner:
            attendee = {'email': group.owner.user.email}
            attendees.append(attendee)
        code = str(res) + "_" + "group_" + str(group.pk)  
    
    if meeting_details['repeat_meet'] == "Δεν Επαναλαμβάνεται" or meeting_details['start'] == 'now':
        recurrence = None
    else:
        repeat_until = meeting_details['repeat_times'].replace('-','')
        repeat_until = repeat_until.replace(':','') + '00Z'
        recurrence = 'RRULE:FREQ='+ meeting_details['repeat_meet'] + ';UNTIL='+ repeat_until


    #google event
    event = {
            'summary': meeting_details['meet_title'],
            'description': meeting_details['meet_desc'],
            'start': {
                'dateTime': start.isoformat("T"),
                'timeZone': 'Europe/Athens',
            },
            'end': {
                'dateTime': end.isoformat("T"),
                'timeZone': 'Europe/Athens',
            },

            'attendees': attendees,

            'recurrence': [
                recurrence
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": code,
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    },
            },
            'reminders': {
                'useDefault': True,
            },
        }
    }
    event = service.events().insert(calendarId=current_student.calendar_id, sendNotifications = True,conferenceDataVersion = 1,body=event).execute()
    if event == None:
        return
    

    #save to localDB
    iCalUID = event['id']
    event_record = GoogleEvent.objects.create(iCalUID = iCalUID,owner=current_student,course=course,group=group)
    for attendee in attendees_local_db:
        event_record.participants.add(attendee)

    return event

def add_attendee_to_events(user,course,group=None):
    current_user = user
    current_student = Student.objects.get(user=current_user)

    if group == None:
        google_events = GoogleEvent.objects.filter(course=course)
        owner = course.owner
    else:
        google_events = GoogleEvent.objects.filter(group=group)
        owner = group.owner
    
    service = google_service(owner.user,"calendar")
    if service == None:
        return None
    updated_event = []
    for google_event in google_events:
        event = service.events().get(calendarId=owner.calendar_id, eventId=google_event.iCalUID).execute()
        if "attendees" not in event:
            event['attendees'] = []

        event['attendees'].append({"email":user.email})
        google_event.participants.add(current_student)
        updated_event = service.events().update(calendarId=owner.calendar_id, eventId=google_event.iCalUID, sendNotifications = True,body=event).execute()
        
    return updated_event

def remove_attendee_from_events(user,course,group=None):
    current_user = user
    current_student = Student.objects.get(user=current_user)

    if group == None:
        google_events = GoogleEvent.objects.filter(course=course)
        owner = course.owner
    else:
        google_events = GoogleEvent.objects.filter(group=group)
        owner = group.owner
    
    service = google_service(owner.user,"calendar")
    if service == None:
        return None
    updated_event = []
    for google_event in google_events:
        event = service.events().get(calendarId=owner.calendar_id, eventId=google_event.iCalUID).execute()
        if "attendees" not in event:
            event['attendees'] = []

        for i in range(len(event['attendees'])):
            if event['attendees'][i]['email'] == user.email:
                del event['attendees'][i]
                break
        google_event.participants.remove(current_student)
        updated_event = service.events().update(calendarId=owner.calendar_id, eventId=google_event.iCalUID, sendNotifications = True,body=event).execute()
        
    return updated_event


def delete_events(user,course,group=None):
    current_user = user
    current_student = Student.objects.get(user=current_user)
    if group == None:
        google_events = GoogleEvent.objects.filter(course=course)
        owner = course.owner
    else:
        google_events = GoogleEvent.objects.filter(group=group)
        owner = group.owner

    service = google_service(owner.user,"calendar")
    if service == None:
        return None
    
    for google_event in google_events:
        try:
            updated_event = service.events().delete(calendarId=owner.calendar_id, eventId=google_event.iCalUID,sendUpdates ='all').execute()
        except:
            pass
    
    google_events.delete()

    return




def serialize_time(date_time):
    temp = date_time.split('T')
    date = datetime.strptime(temp[0], '%Y-%m-%d').date()
    temp2 = temp[1].split('+')
    temp2[0] = temp2[0].replace("Z","")
    utc_time = datetime.strptime(temp2[0], '%H:%M:%S').time()
    file_modified_local_time = datetime.combine(date, utc_time)

    is_today_event = 0
    if date == date.today():
        is_today_event = 1
    elif date < date.today():
        is_today_event = -1
    return file_modified_local_time , is_today_event

def user_events_list(user,course=None,group=None):
    logger = logging.getLogger("mylogger")
    current_user = user
    current_student = Student.objects.get(user=current_user)

    if course == None and group==None:
        google_events_participant = GoogleEvent.objects.filter(participants=current_student)
        google_events_owner = GoogleEvent.objects.filter(owner=current_student)
    elif course != None:
        google_events_participant = GoogleEvent.objects.filter(participants=current_student,course=course)
        google_events_owner = GoogleEvent.objects.filter(owner=current_student,course=course)
    else:
        google_events_participant = GoogleEvent.objects.filter(participants=current_student,group=group)
        google_events_owner = GoogleEvent.objects.filter(owner=current_student,group=group)
    
    service = google_service(user,"calendar")
    if service == None:
        return None

    event_list_today = []
    event_list_other = []

    
    instances_list_today = []
    instances_list_other = []

    for google_event in google_events_owner:
        all_instances = []
        try:
            event = service.events().get(calendarId=current_student.calendar_id,eventId=google_event.iCalUID).execute()
        except: continue
        if event['status'] == 'cancelled':
            continue
        page_token = None
        while True:
            try:
                instances = service.events().instances(calendarId=current_student.calendar_id, eventId=google_event.iCalUID,pageToken=page_token).execute()
            except : continue
            for instance in instances['items']:
                all_instances.append(instance)
            page_token = instances.get('nextPageToken')
            if not page_token:
                break
        
        event['start'],is_today_event = serialize_time(event['start']['dateTime'])
        event['end'],some = serialize_time(event['end']['dateTime'])

        custom_event = {
            'id':event['id'],
            'summary':event['summary'],
            'start': event['start'],
            'end' : event['end'],
            'hangoutLink' : event['hangoutLink'],
            'database_pk' : google_event.pk,
            'is_today_event':is_today_event
        }            
        if is_today_event == 1 and len(all_instances)==0:
            event_list_today.append(custom_event)
        elif is_today_event == 0 and len(all_instances)==0:
            event_list_other.append(custom_event)
        

        for insance in all_instances:
            #change RFC 3339 UTC to local datetime
            insance['start'],is_today_event = serialize_time(insance['start']['dateTime'])
            insance['end'],some = serialize_time(insance['end']['dateTime'])

            custom_instance = {
                'id':insance['id'],
                'summary':insance['summary'],
                'start': insance['start'],
                'end' : insance['end'],
                'hangoutLink' : insance['hangoutLink'],
                'database_pk' : google_event.pk,
                'is_today_event':is_today_event
            }

            if is_today_event == 1:
                instances_list_today.append(custom_instance)
            elif is_today_event == 0:
                instances_list_other.append(custom_instance)
    
    for google_event in google_events_participant:
        all_instances = []
        try:
            event = service.events().get(calendarId='primary',eventId=google_event.iCalUID).execute()
        except: continue
        if event['status'] == 'cancelled':
            continue
        page_token = None
        while True:
            try:
                instances = service.events().instances(calendarId='primary', eventId=google_event.iCalUID,pageToken=page_token).execute()
            except :continue
            for instance in instances['items']:
                all_instances.append(instance)
            page_token = instances.get('nextPageToken')
            if not page_token:
                break
        

        event['start'],is_today_event = serialize_time(event['start']['dateTime'])
        event['end'],some = serialize_time(event['end']['dateTime'])

        custom_event = {
            'id':event['id'],
            'summary':event['summary'],
            'start': event['start'],
            'end' : event['end'],
            'hangoutLink' : event['hangoutLink'],
            'database_pk' : google_event.pk,
            'is_today_event':is_today_event
        }            


        if is_today_event == 1 and len(all_instances)==0:
            event_list_today.append(custom_event)
        elif is_today_event == 0 and len(all_instances)==0:
            event_list_other.append(custom_event)
        

        for insance in all_instances:
            #change RFC 3339 UTC to local datetime
            insance['start'],is_today_event = serialize_time(insance['start']['dateTime'])
            insance['end'],some = serialize_time(insance['end']['dateTime'])
            custom_instance = {
                'id':insance['id'],
                'summary':insance['summary'],
                'start': insance['start'],
                'end' : insance['end'],
                'hangoutLink' : insance['hangoutLink'],
                'database_pk' : google_event.pk,
                'is_today_event':is_today_event
            }

            if is_today_event == 1:
                instances_list_today.append(custom_instance)
            elif is_today_event == 0:
                instances_list_other.append(custom_instance)


    event_list_today += instances_list_today
    event_list_other += instances_list_other

    event_list_today.sort(key=operator.itemgetter('start'))
    event_list_other.sort(key=operator.itemgetter('start'))
    event_list_other = event_list_other[0:5]



    return event_list_today,event_list_other

