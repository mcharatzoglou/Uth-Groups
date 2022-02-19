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
import json
from django.contrib.auth import logout



#google api
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from allauth.socialaccount.models import SocialToken, SocialApp

def callback(request_id, response, exception):
    if exception:
        print(exception)


def google_service(user,service_name):

    token_object = SocialToken.objects.get(account__user=user, account__provider='google')

    
    time_token_left = token_object.expires_at.timestamp() - datetime.datetime.utcnow().timestamp()

    if time_token_left < 60: # afinw 1 lepto avatza sto token gia pan endexomeno
        refresh_token = token_object.token_secret
        post_data = {
            'client_id': 'CLIENT_ID',
            'client_secret': 'CLIENT_SECRET',
            'refresh_token': token_object.token_secret,
            'grant_type': "refresh_token"
        }
        response = requests.post('https://www.googleapis.com/oauth2/v4/token', data=post_data)
        try:
            token_object.token = response.json()['access_token']
            token_object.token_secret = refresh_token
            token_object.expires_at = datetime.datetime.now() + datetime.timedelta(seconds= response.json()['expires_in'])
            token_object.save()
        except KeyError:
            return None #refresh token expired , (60 meres adranias kanoun inactive to refresh token)
    credentials = Credentials(
        token=token_object.token,
        refresh_token=token_object.token_secret,
        token_uri='https://oauth2.googleapis.com/token',
        client_id='CLIENT_ID',
        client_secret='CLIENT_SECRET')

    service = build(service_name, 'v3', credentials=credentials)
    
    return service

def check_file_id(user,file_id):
    logger = logging.getLogger("mylogger")
    user_object = User.objects.get(pk=user.pk)
    drive_service = google_service(user_object,"drive")
    if drive_service == None:
        return None
    try:
        current_student = Student.objects.get(user=user_object)
        drive_service.files().get(fileId=file_id,supportsAllDrives=True).execute()
    except Exception as err:
        logger.info(err)
        return None
    
    return file_id


def create_file(user,file_metadata,media=None):
    logger = logging.getLogger("mylogger")
    user_object = User.objects.get(pk=user.pk)
    drive_service = google_service(user_object,"drive")
    if drive_service == None:
        return None
    try:
        if media == None:  
            service_create =  drive_service.files().create(body=file_metadata,fields='id').execute()
        else:
            service_create =  drive_service.files().create(body=file_metadata,media_body=media,fields='id').execute()
        return service_create
    except Exception as err:
        logger.info(err)
        return None

def delete_file(file_id,requester_user):
    logger = logging.getLogger("mylogger")
    requester_user_object = User.objects.get(pk=requester_user.pk)
    if check_file_id(requester_user_object,file_id) == None:
        logger.info("Check file id failed\n")
        return None
    drive_service = google_service(requester_user_object,"drive")
    if drive_service == None:
        logger.info("Error in google service\n")
        return None #token expired
    try:
        service_update = drive_service.files().delete(fileId=file_id,supportsAllDrives=True).execute()
        return service_update
    except Exception as err:
        logger.info(err)
        return None


def share_file(file_id,owner_user,requester_user):
    owner_user_object = User.objects.get(pk=owner_user.pk)
    requester_user_object = User.objects.get(pk=requester_user.pk)

    if check_file_id(owner_user_object,file_id) == None:
        return None

    drive_service = google_service(owner_user_object,"drive")
    if drive_service == None:
        return None

    batch = drive_service.new_batch_http_request(callback=callback)
    if batch == None:
        return None

    user_permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': requester_user_object.email
    }
    batch.add(drive_service.permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
    ))

    batch.execute()
    
    return 1

def stop_share_file(file_id,owner_user,requester_user):
    owner_user_object = User.objects.get(pk=owner_user.pk)
    requester_user_object = User.objects.get(pk=requester_user.pk)
    
    if check_file_id(owner_user_object,file_id) == None:
        return None

    drive_service = google_service(owner_user_object,"drive")
    if drive_service == None:
        return None
    
    try:
        permissions = drive_service.permissions().list(fileId=file_id,fields="permissions(kind,id,type,emailAddress,domain,role,displayName,expirationTime)").execute()
    except Exception:
        return None
    
    
    permission_id = 0
    for perm in permissions['permissions']:
        if requester_user.email == perm['emailAddress']:
            permission_id = perm['id']
            break
    
    
    if permission_id == 0:
        return None
    batch = drive_service.new_batch_http_request(callback=callback)
    if batch == None:
        return None
    batch.add(drive_service.permissions().delete(
            fileId=file_id,
            permissionId=permission_id
    ))

    batch.execute()

    return 1



def delete_shorcut(file_id,requester_user):
    requester_user_object = User.objects.get(pk=requester_user.pk)
    if check_file_id(requester_user_object,file_id) == None:
        return None
    drive_service = google_service(requester_user_object,"drive")
    if drive_service == None:
        return None #token expired
    try:
        service_update = drive_service.files().delete(fileId=file_id).execute()
        return service_update
    except Exception as err:
        logger = logging.getLogger("mylogger")
        logger.info(err)
        return None
    return None

def retrieve_all_files_in_folder(user,file_id):
    logger = logging.getLogger("mylogger")
    requester_user_object = User.objects.get(pk=user.pk)
    q = "\"" + file_id + "\"" + " in parents and "+ "trashed = false"
    result = []
    page_token = None

    if check_file_id(requester_user_object,file_id) == None:
        return None,None

    drive_service = google_service(requester_user_object,"drive")
    if drive_service == None:
        return None,None #token expired

    try:
        while True:
            if page_token:
                service_list = drive_service.files().list(q=q,pageToken=page_token,fields='webContentLink').execute()
            else:
                service_list = drive_service.files().list(q=q,fields='files(kind,id,name,mimeType,iconLink,webContentLink,modifiedTime,webViewLink,lastModifyingUser,owners)').execute()
            page_token = service_list.get('nextPageToken')
            result.extend(service_list.get('files'))

            if not page_token:
                break
        parent = drive_service.files().get(fileId=file_id,fields="parents").execute()
        try:
            parent = parent['parents'][0]
            logger.info(parent)
        except:
            parent = None
        return service_list,parent
    except Exception as err:
        logger.info(err)
        return None,None
    return None,None

#uploaders
def drive_usage(requester_user):
    logger = logging.getLogger("mylogger")
    requester_user_object = User.objects.get(pk=requester_user.pk)
    drive_service = google_service(requester_user_object,"drive")
    if drive_service == None:
        logger.info("DRIVE_USAGE : GOOGLE_SERVICE RETURN NONE FOR UPLOADER")
        return None #token expired
    try:
        service_update = drive_service.about().get(fields="storageQuota").execute()
        return service_update
    except Exception as err:
        logger = logging.getLogger("mylogger")
        logger.info(err)
        return None