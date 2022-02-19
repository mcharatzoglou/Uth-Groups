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

@login_required(login_url='home')
@is_student
def change_private(request):
    group_id = request.GET['group_id']
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    group = Group.objects.get(pk=group_id)
    if current_student == group.owner or current_student in group.admins.all():
        if group.private == False:
            group.private = True
        else:
            group.private = False
        group.save()
    return HttpResponse('')


@login_required(login_url='home')
@is_student
def create_code(request):
    group_id = request.GET['group_id']
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    group = Group.objects.get(pk=group_id)
    if current_student == group.owner or current_student in group.admins.all():   
        res = ''.join(secrets.choice(string.ascii_letters + string.digits) for x in range(10))
        while(1):
            code = str(res)
            if Group.objects.filter(pk=group_id,code=code).exists() or Course.objects.filter(code=code).exists():
                continue
            else:
                group.code = code
                group.save()
                context = {'current_group':group}
                return render(request, 'uth_groups_app/authenticated/groups/group_changes.html',context)
    return HttpResponse('')

@login_required(login_url='home')
@is_student
def delete_code(request):
    group_id = request.GET['group_id']
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    group = Group.objects.get(pk=group_id)
    if current_student == group.owner or current_student in group.admins.all():
        group.code = None
        group.save()
        context = {'current_group':group}
        return render(request, 'uth_groups_app/authenticated/groups/group_changes.html',context)
    return HttpResponse('')

#team
@login_required(login_url='home')
@is_student
def team_change_private(request):
    team_id = request.GET['course_id']
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    team = Course.objects.get(pk=team_id)
    if current_student == team.owner or current_student in team.admins.all():
        if team.private == False:
            team.private = True
        else:
            team.private = False
        team.save()
    return HttpResponse('')


@login_required(login_url='home')
@is_student
def team_create_code(request):
    team_id = request.GET['course_id']
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    team = Course.objects.get(pk=team_id)
    if current_student == team.owner or current_student in team.admins.all():   
        res = ''.join(secrets.choice(string.ascii_letters + string.digits) for x in range(10))
        while(1):
            code = str(res)
            if Course.objects.filter(pk=team_id,code=code).exists() or Group.objects.filter(code=code).exists():
                continue
            else:
                team.code = code
                team.save()
                context = {'course':team}
                return render(request, 'uth_groups_app/authenticated/courses/team_changes.html',context)
    return HttpResponse('')

@login_required(login_url='home')
@is_student
def team_delete_code(request):
    team_id = request.GET['course_id']
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    team = Course.objects.get(pk=team_id)
    if current_student == team.owner or current_student in team.admins.all():
        team.code = None
        team.save()
        context = {'course':team}
        return render(request, 'uth_groups_app/authenticated/courses/team_changes.html',context)
    return HttpResponse('')