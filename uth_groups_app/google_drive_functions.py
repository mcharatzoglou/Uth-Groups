from .google import *
import requests
from django.shortcuts import render, redirect
from .decorators import *
from django.http import HttpResponse , HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from allauth.account.views import SignupView, LoginView
from .models import *
import logging
import datetime
import time
from django.contrib.auth import logout
from hurry.filesize import size
import os.path
from mimetypes import MimeTypes
from datetime import date, datetime, time, timedelta

#google api
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from allauth.socialaccount.models import SocialToken, SocialApp
from .google_calendar_functions import *


def create_team(user,team_data):
    current_user = user
    current_student = Student.objects.get(user=current_user)

    logger = logging.getLogger("mylogger")

    if check_file_id(user,current_student.root_folder_id) == None:
        logger.info("CHECK FILE ID FAILED\n")
        return None

    uploader = pick_uploader()
    if uploader == None:
        logger.info("CANT PICK UPLOADER\n")
        return None

    file_metadata = {
        'name': team_data['team_name'],
        'description': team_data['description'],
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [uploader.base_id]
    }
    state = create_file(uploader.user,file_metadata)
    if state == None:
        logger.info("CREATE_FILE RETURN NONE\n")
        return None

    file_metadata2 = {
        'name': team_data['team_name'] + " Αρχεία",
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [state.get('id')]
    }
    state2 = create_file(uploader.user,file_metadata2)
    if state2 == None:
        logger.info("CREATE_FILE RETURN NONE\n")
        return None
        
    team = Course.objects.create(
        owner= current_student,
        course_name = team_data['team_name'],
        private = team_data['private'],
        datetime=(datetime.now()).strftime("%d/%m/%Y, %H:%M:%S"),
        folder_id = state.get('id'),
        files_folder_id= state2.get('id')
    )

    if team == None:
        logger.info("CREATE DATABASE RECORD FAILED\n")
        return None

    #user folders
    file_metadata3 = {
        'name': team_data['team_name'],
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [current_student.root_folder_id]
    }
        
    user_team_folder = create_file(user,file_metadata3)

    if user_team_folder == None:
        logger.info("CREATE USER FOLDER FAILED\n")
        return None
    
    state3 = share_file(team.files_folder_id,uploader.user,user)
    if state3 == None:
        logger.info("SHARE USER FOLDER FAILED\n")
        return None
    
    file_metadata4 = {
        'name': team_data['team_name'] + " Αρχεία", 
        'mimeType': 'application/vnd.google-apps.shortcut',
        'description': 'Έγινε share μέσω Uth Groups.',
        'parents': [user_team_folder.get('id')],
        'shortcutDetails': {
            'targetId': state2.get('id')
            }
    }
                
    state4 = create_file(user,file_metadata4)
    if state4 == None:
        return None

    user_ids = Course_root_folders_ids.objects.create(
        student = current_student,
        course= team,
        root_id= user_team_folder.get('id'),
        root_files_id=state4.get('id')
    )
    if user_ids == None:
        return None
    

    return team

def delete_team(user,team):
    current_student = Student.objects.get(user=user)

    participants = team.participants.all()
    for participant in participants:
        leave_team(participant.user,team)
    
    state = leave_team(user,team)
    delete_events(user,team)
    team.delete()

    return state

def join_team(user,team):
    current_user = user
    current_student = Student.objects.get(user=current_user)

    if check_file_id(user,current_student.root_folder_id) == None:
        return None

    uploader = pick_uploader()
    if uploader == None:
        return None

    #user folders
    file_metadata = {
        'name': team.course_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [current_student.root_folder_id]
    }
        
    user_team_folder = create_file(user,file_metadata)

    if user_team_folder == None:
        return None
    
    state = share_file(team.files_folder_id,uploader.user,user)
    if state == None:
        return None
    
    file_metadata2 = {
        'name': team.course_name + " Αρχεία",
        'mimeType': 'application/vnd.google-apps.shortcut',
        'description': 'Έγινε share μέσω Uth Groups.',
        'parents': [user_team_folder.get('id')],
        'shortcutDetails': {
            'targetId': team.files_folder_id
            }
    }
                
    state2 = create_file(user,file_metadata2)

    if state2 == None:
        return None

    user_ids = Course_root_folders_ids.objects.create(
        student = current_student,
        course= team,
        root_id= user_team_folder.get('id')
    )
    if user_ids == None:
        return None

    team.participants.add(current_student)
 

    return 1

def leave_team(user,team):
    current_user = user
    current_student = Student.objects.get(user=current_user)
    groups_as_participant = Group.objects.filter(participants=current_student,course=team)
    groups_as_owner = Group.objects.filter(owner=current_student,course=team)

    uploader = pick_uploader()
    if uploader == None:
        return None

    for group in groups_as_participant:
        leave_group(current_user,group)
    
    for group in groups_as_owner:
        delete_group(current_user,group)
    
    user_team_folder = Course_root_folders_ids.objects.filter(student=current_student,course=team)


    stop_share = stop_share_file(team.files_folder_id,uploader.user,user)
    if stop_share == None:
        return None

    remove_attendee_from_events(user,team)
    
    for item in user_team_folder:
        delete_file(item.root_id,current_user)
        item.delete()
    team.join_requests.remove(current_student)
    team.participants.remove(current_student)
    team.admins.remove(current_student)
    
    return 

def create_group(user,team,group_data):
    current_user = user
    current_student = Student.objects.get(user=current_user)
    user_team_files = Course_root_folders_ids.objects.get(student=current_student,course=team)
    
    if check_file_id(user,user_team_files.root_id) == None:
        return None
    
    file_metadata = {
        'name': group_data['group_name'],
        'mimeType': 'application/vnd.google-apps.folder',
        'description': group_data['description'],
        'parents': [team.folder_id]
    }

    uploader = pick_uploader()
    if uploader == None:
        return None
    group_dir = create_file(uploader.user,file_metadata)

    if group_dir == None:
        return None
    
    state = share_file(group_dir.get('id'),uploader.user,user)
    if state == None:
        return None
    
    file_metadata2 = {
        'name': group_data['group_name'],
        'mimeType': 'application/vnd.google-apps.shortcut',
        'description': 'Έγινε share μέσω Uth Groups.',
        'parents': [user_team_files.root_id],
        'shortcutDetails': {
            'targetId': group_dir.get('id')
            }
    }
                
    state2 = create_file(user,file_metadata2)

    if state2 == None:
        return None


    group = Group.objects.create(
        owner=current_student,
        title=group_data['group_name'],
        datetime=(datetime.now()).strftime("%d/%m/%Y, %H:%M:%S"),
        description=group_data['description'],
        course=team,
        private = group_data['private'],
        root_id = group_dir.get('id')
    )

    Group_root_folders_ids.objects.create(
        student=current_student,
        group=group,
        root_id=group_dir.get('id'),
        shorcut_id=state2.get('id')
    )

    return group

def delete_group(user,group):
    current_student = Student.objects.get(user=user)
    participants = group.participants.all()
    course = Course.objects.get(pk=group.course.pk)
    uploader = pick_uploader()
    if uploader == None:
        return None

    for participant in participants:
        leave_group(participant.user,group)
    
    user_group_files = Group_root_folders_ids.objects.get(student=current_student,group=group)

    stop_share = stop_share_file(group.root_id,uploader.user,user)
    if stop_share == None:
        return None

    delete = delete_shorcut(user_group_files.shorcut_id,user)
    delete_events(user,course,group)
    user_group_files.delete()
    group.delete()

    return delete

def join_group(user,group):
    current_student = Student.objects.get(user=user)
    team = Course.objects.get(pk=group.course.pk)
    user_team_files = Course_root_folders_ids.objects.get(student=current_student,course=team)

    if check_file_id(user,user_team_files.root_id) == None:
        return None

    uploader = pick_uploader()
    if uploader == None:
        return None

    
    state = share_file(group.root_id,uploader.user,user)
    if state == None:
        return None

    file_metadata = {
        'name': group.title,
        'mimeType': 'application/vnd.google-apps.shortcut',
        'description': 'Έγινε share μέσω Uth Groups.',
        'parents': [user_team_files.root_id],
        'shortcutDetails': {
        'targetId': group.root_id
            }
    }
                
    user_shorcut_dir = create_file(user,file_metadata)
    if user_shorcut_dir == None:
        return None

    group.participants.add(current_student)
    Group_root_folders_ids.objects.create(
        student=current_student,
        group=group,
        root_id=group.root_id,
        shorcut_id=user_shorcut_dir.get('id')
    )

    return group

def leave_group(user,group):
    current_user = User.objects.get(pk=user.pk)
    current_student = Student.objects.get(user=current_user)
    team = Course.objects.get(pk=group.course.pk)
    user_group_files = Group_root_folders_ids.objects.get(student=current_student,group=group)

    uploader = pick_uploader()
    if uploader == None:
        return None

    stop_share = stop_share_file(group.root_id,uploader.user,current_user)
    if stop_share == None:
        return None

    delete = delete_shorcut(user_group_files.shorcut_id,current_user)
    user_group_files.delete()
    group.participants.remove(current_student)
    group.join_requests.remove(current_student)
    group.admins.remove(current_student)
    remove_attendee_from_events(user,team,group)
    


    return stop_share


def folder_data(user,file_id):
    logger = logging.getLogger("mylogger")
    requester_user_object = User.objects.get(pk=user.pk)
    current_student = Student.objects.get(user=requester_user_object)
    files,parent = retrieve_all_files_in_folder(requester_user_object,file_id)
    if files == None:
        return None,None
    for file in files['files']:
        extension = os.path.splitext(file['name'])[1][1:]
        if extension == "":
            if not file['mimeType'].find("application/vnd.google-apps.folder"): 
                file['svg'] = "folder.svg"
            else: #custom google mimetypes -> https://developers.google.com/drive/api/v3/mime-types
                file['svg'] = "blank.svg" 
        else:
            file['svg'] = extension + ".svg"
        
        #change RFC 3339 UTC to local datetime
        temp = file['modifiedTime'].split('T')
        date = datetime.strptime(temp[0], '%Y-%m-%d').date()
        temp2 = temp[1].split('.')
        utc_time = datetime.strptime(temp2[0], '%H:%M:%S').time()
        file_modified_local_time = datetime.combine(date, utc_time) + timedelta(hours=3)
        file['modifiedTime'] = file_modified_local_time
        
        file['iconLink'] = file['iconLink'].replace("16","256")
    if files == None:
        return None,None
    return files,parent



#UPLOADERS FUNCTIONS
def add_uploader(request):
    current_user = request.user
    current_uploader = Uploader.objects.get(user=current_user)

    owner_user = User.objects.get(email="uthgroups.uploader1@gmail.com")
    owner_uploader = Uploader.objects.get(user=owner_user)

    state = share_file(owner_uploader.base_id,owner_user,current_user)

    if state != None:
        current_uploader.base_id = owner_uploader.base_id
        current_uploader.active = True
        current_uploader.save()
        return 1
    return None

def pick_uploader():
    logger = logging.getLogger("mylogger")
    uploaders = Uploader.objects.filter(active=True)
    biggest_available_space = 0
    pick_uploader = None
    for uploader in uploaders:
        
        about = drive_usage(uploader.user)
        if about == None:
            logger.info("PICK_UPLOADER : DRIVE USAGE RETURN NONE")
            return None
        uploader.total_space = int(about['storageQuota']['limit'])
        uploader.total_space_str = size(int(about['storageQuota']['limit']))

        uploader.used_space = int(about['storageQuota']['usage'])
        uploader.used_space_str = size(int(about['storageQuota']['usage']))

        uploader.available_space = int(about['storageQuota']['limit']) - int(about['storageQuota']['usage'])
        uploader.available_space_str = size(int(about['storageQuota']['limit']) - int(about['storageQuota']['usage']))

        uploader.used_space = int(about['storageQuota']['usage'])
        uploader.used_space_str = size(int(about['storageQuota']['usage']))

        uploader.save()

        if biggest_available_space < uploader.available_space:
            biggest_available_space = uploader.available_space
            pick_uploader = uploader

    return pick_uploader

def pick_uploader_to_delete(file_id):
    uploaders = Uploader.objects.filter(active=True)
    pick_uploader = None
    for uploader in uploaders:
        state = check_file_id(uploader.user,file_id)
        if state == file_id:
            logger = logging.getLogger("mylogger")
            logger.info("uploader found\n")
            return uploader
    return pick_uploader

def upload_file_to_drive(user,folder_id,file):
    current_user = User.objects.get(pk=user.pk)
    current_student = Student.objects.get(user=current_user)

    uploader = pick_uploader()
    if uploader == None:
        return None
    
    logger = logging.getLogger("mylogger")
    filename = os.path.splitext(file.name)[0]
    extension = os.path.splitext(file.name)[1][1:]
    mime = MimeTypes()
    mime_type = mime.guess_type(file.name)[0]
    if mime_type == None:
        mime_type = "application/octet-stream"
    logger.info(mime_type)

    logger.info(filename)
    logger.info(extension)

    file_metadata = {
        'name': filename,
        'mimeType': mime_type,
        'parents': [folder_id]
    }

    file_db = UploadedFile.objects.create(
        student = current_student,
        folder_id = folder_id,
        filename = file.name,
        file = file
    )

    if file_db == None:
        return None

    path = file_db.file.path
    media = MediaFileUpload(path, mimetype = mime_type)
    create_file(uploader.user,file_metadata,media)

    return file_db

def create_directory_drive(user,folder_id,folder_name):
    current_user = User.objects.get(pk=user.pk)
    current_student = Student.objects.get(user=current_user)
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [folder_id]
    }
    uploader = pick_uploader()
    if uploader == None:
        return None
    state = create_file(uploader.user,file_metadata)
    return state

def deletefilefolder_drive(user,filefolderid):
    current_user = User.objects.get(pk=user.pk)
    current_student = Student.objects.get(user=current_user)
    state = delete_file(filefolderid,current_user)
    return state

