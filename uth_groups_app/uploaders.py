import requests
from django.shortcuts import render, redirect
from .decorators import *
from django.http import HttpResponse , HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from allauth.account.views import SignupView, LoginView
from .models import *
from .google import *
from .google_drive_functions import *
import logging
import datetime
import time
from itertools import chain
from django.contrib.auth import logout
from hurry.filesize import size
import random,string,secrets
from .forms import UploadFileForm
from .team_and_group_changes import *


@login_required(login_url='home')
@is_uploader
def control(request):
    current_user = request.user
    current_uploader = Uploader.objects.get(user=current_user)
    uploaders = Uploader.objects.all()
    
    
    logger = logging.getLogger("mylogger")
    logger.info(pick_uploader())
    
    uploaders_active = Uploader.objects.filter(active=True)
    total_available_space = 0
    for uploader in uploaders_active:
        total_available_space+= uploader.available_space
    
    total_available_space_str = size(total_available_space)

    if request.method == 'POST':
        logger.info(add_uploader(request))
        current_uploader = Uploader.objects.get(user=current_user)
        return redirect("/control")

    context = {"current_uploader":current_uploader,"uploaders":uploaders,"total_available_space_str":total_available_space_str}
    return render(request, 'uth_groups_app/authenticated/uploaders/control.html',context)

@login_required(login_url='home')
@is_uploader
def initdrive(request):
    current_user = request.user
    current_uploader = Uploader.objects.get(user=current_user)
    file_metadata = {
        'name': 'Uth Groups Files',
        'mimeType': 'application/vnd.google-apps.folder'
        }
    base_dir = create_file(request.user,file_metadata)
    if  base_dir != None:
        current_uploader.active = True
        current_uploader.base_id = base_dir['id']
        current_uploader.save()
    return render(request, 'uth_groups_app/authenticated/uploaders/control.html')

@login_required(login_url='home')
@is_student
def renderfolder(request,folderID=None):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    if folderID == None:
        folder_id = request.GET['folder_id']
    else:
        folder_id = folderID
    user_folder_data,parent_folder = folder_data(current_user,folder_id)
    if user_folder_data != None:
        user_folder_data = user_folder_data['files']
    context = {"request":request,'selected_tab':-1,"user_folder_data":user_folder_data,"parent_folder":parent_folder,"folder_id":folder_id}
    return render(request, 'uth_groups_app/authenticated/files/renderfiles.html',context)

@login_required(login_url='home')
@is_student
def upload_file(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            folder_id = request.POST.get('current_folder_id',False)
            uploaded_files = request.FILES.getlist('files')
            for f in uploaded_files:
                file_db = upload_file_to_drive(current_user,folder_id,f)
                file_db.delete()
            return renderfolder(request,folder_id)
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})

@login_required(login_url='home')
@is_student
def create_folder(request):
    logger = logging.getLogger("mylogger")
    
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    
    if request.method == 'POST':
        folder_name = request.POST.get('folderName',False)
        folder_id = request.POST.get('current_folder_id',False)
        if folder_name == False or folder_id == False:
            return HttpResponseRedirect("")
        state = create_directory_drive(current_user,folder_id,folder_name)
        return renderfolder(request,folder_id)

    return HttpResponseRedirect("")