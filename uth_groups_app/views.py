import requests
from django.shortcuts import render, redirect
from .decorators import *
from django.http import HttpResponse , HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from allauth.account.views import SignupView, LoginView
from .models import *
from .google import *
from .google_drive_functions import *
from .google_calendar_functions import *
import logging
import datetime
import time
from itertools import chain, groupby
from django.contrib.auth import logout
from hurry.filesize import size
import random,string,secrets
from .forms import UploadFileForm
from .team_and_group_changes import *
from .uploaders import *
from .academic_verification import *
from datetime import datetime
from django.contrib import messages



#views
@unauthenticated_user
def index(request):
    context = {"request":request}
    return render(request, 'uth_groups_app/landing/home.html',context)

@unauthenticated_user
def privacypolicy(request):
    context = {"request":request}
    return render(request, 'uth_groups_app/landing/privacypolicy.html',context)

@unauthenticated_user
def about(request):
    context = {"request":request}
    return render(request, 'uth_groups_app/landing/about.html',context)

@login_required(login_url='home')
@is_student
def dashboard(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    myteams1 = Course.objects.filter(participants=current_student).order_by('-course_name')
    myteams2 = Course.objects.filter(owner=current_student).order_by('-course_name')
    myteams = list(chain(myteams1,myteams2))
    context = {"request":request,'myteams':myteams}
    return render(request, 'uth_groups_app/authenticated/dashboard/dashboard.html',context)

@login_required(login_url='home')
@is_student
def calendar(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    event_list_today,event_list_other = user_events_list(current_user)
    context = {"request":request,"event_list_today":event_list_today,"event_list_other":event_list_other}
    return render(request, 'uth_groups_app/authenticated/dashboard/calendar.html',context)

@login_required(login_url='home')
@is_student
def profile(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    context = {"request":request,"current_student":current_student}
    return render(request, 'uth_groups_app/authenticated/dashboard/profile.html',context)


@login_required(login_url='home')
def new(request): 
    current_user = request.user
    
    try:
        current_student = Student.objects.get(user=current_user)
    except Student.DoesNotExist:
        current_student = None
    
    request.session.set_expiry(3600)
    
    if current_student == None:
        current_student = Student.objects.create(user=current_user)

    if current_student.is_academic_authorized == False:
        return HttpResponseRedirect('/academicAuthorization')
    else:
        return HttpResponseRedirect('/dashboard')

@login_required(login_url='home')
def academicAuthorization(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)

    if current_student.is_academic_authorized == True:
        return HttpResponseRedirect('/dashboard')

    if request.method == "POST":
        #POST request comes from academic_authorization.html
        if current_student.authorization_code == None:
            academic_email = request.POST.get('academic_email',False)
            if academic_email == False:
                messages.error(request,"Κάτι πήγε στραβά")
                return HttpResponseRedirect('/academicAuthorization')
            
            academic_email = academic_email.split("@",1)[0] + "@uth.gr"
            res = ''.join(secrets.choice(string.ascii_letters + string.digits) for x in range(15))
            code = str(res)
            current_student.authorization_code = code
            current_student.academic_email = academic_email
            current_student.save()
            send_verification_email(current_user)
            return HttpResponseRedirect('/academicAuthorization')
        #POST request comes from academic_authorization_2.html
        else:
            code = request.POST.get('code',False)
            if code == current_student.authorization_code:
                current_student.is_academic_authorized = True
                current_student.save()
                file_metadata = {
                    'name': 'Uth Groups',
                    'mimeType': 'application/vnd.google-apps.folder',
                    "folderColorRgb": 'red'
                }
                file = create_file(current_user,file_metadata)
                calendar_id = create_calendar(current_user)
                if (file == None) or (calendar_id == None):
                    logout(request)
                    current_student.delete()
                    return redirect('dashboard')
                current_student.calendar_id = calendar_id
                current_student.root_folder_id = file['id']
                current_student.save()
                return HttpResponseRedirect('/dashboard')
            else:
                return HttpResponseRedirect('/academicAuthorization')

    if current_student.authorization_code == None:
        return render(request, 'uth_groups_app/authenticated/register/academic_authorization.html')
    else:
        return render(request, 'uth_groups_app/authenticated/register/academic_authorization_2.html')

@login_required(login_url='home')
def backAcademicAuthorization(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)

    current_student.academic_email = None
    current_student.authorization_code = None
    current_student.save()

    return HttpResponseRedirect('/academicAuthorization')

@login_required(login_url='home')
def cancelAcademicAuthorization(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)

    current_user.delete()
    logout(request)

    return redirect('home')

@login_required(login_url='home')
def logout_user(request):
    logout(request)
    return redirect('home')
    
@login_required(login_url='home')
@is_student
def search(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    enrolled_courses = Course.objects.filter(participants=current_student).order_by('-course_name')
    context = {"request":request,'enrolled_courses':enrolled_courses}
    return render(request, 'uth_groups_app/authenticated/search_group/find_study_group.html',context)

@login_required(login_url='home')
@is_student
def groupsearch(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    search = request.GET['searched']
    if search != "" and search != " ":
        results = Course.objects.filter(course_name__icontains=search).order_by('-course_name')
    else:
        results = None
    context = {"results": results }
    return render(request, 'uth_groups_app/authenticated/search_group/render_groups.html',context)

@login_required(login_url='home')
@is_student
def add_course(request):
    course_pk = int(request.GET['strID'])
    state = int(request.GET['strState'])

    current_user = request.user
    current_student = Student.objects.get(user=current_user)

    course_to_enroll = Course.objects.get(id=course_pk)
    drive_service = google_service(current_user,"drive")

    if state == 1:
        if current_student not in course_to_enroll.participants.all():
            #create folders in Google Drive for new user
            join_team(current_user,course_to_enroll)
            add_attendee_to_events(current_user,course_to_enroll)

    else:
        if current_student in course_to_enroll.participants.all():
            try:
                course_files = Course_root_folders_ids.objects.get(student=current_student,course=course_to_enroll)
                status = delete_file(request,course_files.root_id)
                if status == None:
                    logout(request)
                    return redirect('dashboard')
                Course_root_folders_ids.objects.filter(student=current_student,course=course_to_enroll).delete()
                course_to_enroll.participants.remove(current_student)
            except Course_root_folders_ids.DoesNotExist:
                course_to_enroll.participants.remove(current_student)

    return HttpResponse('')

@login_required(login_url='home')
@is_student
@is_course_valid
def coursePage(request,course_id):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    form = UploadFileForm()
    
    try:
        course = Course.objects.get(participants=current_student,id=course_id)
    except Course.DoesNotExist:
        try:
            course = Course.objects.get(owner=current_student,id=course_id)
        except Course.DoesNotExist:
            course = Course.objects.get(id=course_id)
            participants = course.participants.all()
            if request.method == 'POST':
                detector = request.POST.get('key_detection',False)
                private_request = request.POST.get('private_request',False)
                if detector != False and private_request == False:
                    team_dir = join_team(request.user,course)
                    join_request_sended = False
                    for student in course.join_requests.all():
                        if current_student == student:
                            join_request_sended = True
                            break
                    if team_dir == None:
                        context = {
                            "request":request,
                            "course":course,
                            'selected_tab':-1,
                            'participants':participants,
                            'owner':course.owner,
                            'join_request_sended':join_request_sended,
                            'current_student':current_student,
                            "error_message":"Κάτι πήγε στραβά 😥.",
                            "form":form
                        }   
                        return render(request, 'uth_groups_app/authenticated/groups/not_member_coursePage.html',context)
                    add_attendee_to_events(current_user,course)
                elif detector != False and private_request != False:
                    flag = True
                    join_requests = course.join_requests.all()
                    for i in join_requests:
                        if i == current_student:
                            flag = False
                            break
                    if flag == True:
                        course.join_requests.add(current_student)
                        course.save()
                    join_request_sended = False
                    for student in course.join_requests.all():
                        if current_student == student:
                            join_request_sended = True
                            break
                    context = {
                            "request":request,
                            "course":course,
                            'selected_tab':-1,
                            'participants':participants,
                            'owner':course.owner,
                            'current_student':current_student,
                            'join_request_sended': join_request_sended,
                            "form":form
                        } 
                    return render(request, 'uth_groups_app/authenticated/groups/not_member_coursePage.html',context)
                url = "/course/" + str(course_id)
                return redirect(url)

            join_request_sended = False
            for student in course.join_requests.all():
                if current_student == student:
                    join_request_sended = True
                    break
                
            context = {
                "request":request,
                "course":course,
                'selected_tab':-1,
                'participants':participants,
                'owner':course.owner,
                'join_request_sended':join_request_sended,
                "form":form
            }
            return render(request, 'uth_groups_app/authenticated/groups/not_member_coursePage.html',context)

    selected_tab = -1 # -1 = course Page

    mygroups = Group.objects.filter(course=course)
    
    try:
        participants = course.participants.all()
    except Course.DoesNotExist:
        participants = None
    
    if request.method == 'POST':
        remove_course = request.POST.get('remove_course',False)
        if (remove_course != False):
            if current_student == course.owner:
                delete_team(current_user,course)     
            else:
                leave_team(current_user,course)
                            
            return HttpResponseRedirect('/dashboard')

    user_folder_data,parent_folder = folder_data(current_user,course.files_folder_id)
    if user_folder_data != None:
        user_folder_data = user_folder_data['files']
    event_list_today,event_list_other = user_events_list(current_user,course)
    chat_messages = course.chat_messages.all()
    join_requests = course.join_requests.all()
    admins = course.admins.all()

    context = {
        "request":request,
        "course":course,
        "mygroups":mygroups,
        'selected_tab':selected_tab,
        'participants':participants,
        'join_requests':join_requests,
        'admins':admins,
        'current_student':current_student,
        'owner':course.owner,
        "user_folder_data":user_folder_data,
        "parent_folder":parent_folder,
        "folder_id":course.files_folder_id,
        "form":form,
        "event_list_today":event_list_today,
        "event_list_other":event_list_other,
        "chat_messages":chat_messages

    }
    return render(request, 'uth_groups_app/authenticated/groups/coursePage.html',context)



@login_required(login_url='home')
@is_student
@is_course_valid
@is_course_member
def creategroup(request,course_id):
    course = Course.objects.get(id=course_id)
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    selected_tab = -2 # -2 = new group

    mygroups = Group.objects.filter(course=course)

    if request.method == 'POST':
        group_name = request.POST.get('group_name',False)
        group_description = request.POST.get('description',False)
        private = request.POST.get('private',False)
        if (private == "on"):
            private = True
        group_data = {
        'group_name': group_name,
        'description': group_description,
        'private': private,
        }

        if (not Group.objects.filter(course=course,title=group_name).exists()):
            #google create dirs and group
            group = create_group(request.user,course,group_data)
            if group != None:
                url = "/course/" + str(course_id) + "/group/" + str(group.pk)
                return redirect(url)
            else:
                context = {
                    "request":request,
                    "temp_groupname":group_name,
                    "temp_description":group_description,
                    "temp_private":private,
                    "course":course,
                    'mygroups':mygroups,
                    'selected_tab':selected_tab,
                    "error_message":"Κάτι πήγε στραβά 😥."
                }
                return render(request, 'uth_groups_app/authenticated/groups/createGroup.html',context)
        
        context = {
            "request":request,
            "temp_groupname":group_name,
            "temp_description":group_description,
            "temp_private":private,
            "course":course,
            "message":"Το όνομα του Group υπάρχει ήδη",
            'mygroups':mygroups,
            'selected_tab':selected_tab
        }
        return render(request, 'uth_groups_app/authenticated/groups/createGroup.html',context)


    context = {"request":request,"course":course,'mygroups':mygroups,'selected_tab':selected_tab}
    return render(request, 'uth_groups_app/authenticated/groups/createGroup.html',context)

@login_required(login_url='home')
@is_student
@is_course_valid
@is_group_valid
def groupPage(request,course_id,group_id):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    course = Course.objects.get(id=course_id)
    current_group = Group.objects.get(pk=group_id,course=course)
    selected_tab = int(group_id)


    mygroups = Group.objects.filter(course=course)
    
    try:
        participants = current_group.participants.all()
        owner = current_group.owner
    except Group.DoesNotExist:
        participants = None
        owner = None
    
    is_member = (current_student in current_group.participants.all()) or (current_student == current_group.owner)
    is_owner = current_student == current_group.owner


    
    if request.method == 'POST':
        detector = request.POST.get('key_detection',False)
        private_request = request.POST.get('private_request',False)
        if detector != False and private_request == False:
            url = "/course/" + str(course_id) + "/group/" + str(group_id)
            if is_member:
                if is_owner:
                    #delete group in whice student is owner
                    delete_group(request.user,current_group)
                    return redirect(url)
                else:
                    if leave_group(request.user,current_group) != None:
                        url = "/course/" + str(course_id)
                        return redirect(url)
                    else:
                        return redirect("/dashboard")
            else:    
                group_dir = join_group(request.user,current_group)
                add_attendee_to_events(current_user,course,current_group)
                if group_dir == None:
                    join_request_sended = False
                    for student in current_group.join_requests.all():
                        if current_student == student:
                            join_request_sended = True
                            break
                    context = {
                        "request":request,
                        "course":course,
                        'mygroups':mygroups,
                        'selected_tab':selected_tab,
                        'current_group':current_group,
                        'participants':participants,
                        'join_request_sended':join_request_sended,
                        'owner':owner,
                        'current_student':current_student,
                        "error_message":"Κάτι πήγε στραβά 😥."
                    }
                    return render(request, 'uth_groups_app/authenticated/groups/group_not_member.html',context)
                return redirect(url)
        elif detector != False and private_request != False:
            flag = True
            join_requests = current_group.join_requests.all()
            for i in join_requests:
                if i == current_student:
                    flag = False
                    break
            if flag == True:
                current_group.join_requests.add(current_student)
                current_group.save()


    join_request_sended = False
    for student in current_group.join_requests.all():
        if current_student == student:
            join_request_sended = True
            break
    context = {
        "request":request,
        "course":course,
        'mygroups':mygroups,
        'selected_tab':selected_tab,
        'current_group':current_group,
        'participants':participants,
        'owner':owner,
        'join_request_sended':join_request_sended,
        'current_student':current_student
    }
    if is_member:
        group_dir = Group_root_folders_ids.objects.get(student=current_student,group=current_group).root_id
        user_folder_data,parent_folder = folder_data(current_user,current_group.root_id)
        if user_folder_data != None:
            user_folder_data = user_folder_data['files']
        event_list_today,event_list_other = user_events_list(current_user,course=None,group=current_group)
        context = {
            "request":request,
            "course":course,
            'mygroups':mygroups,
            'selected_tab':selected_tab,
            'current_group':current_group,
            'participants':participants,
            'owner':owner,
            'current_student':current_student,
            'join_requests':current_group.join_requests.all(),
            'admins':current_group.admins.all(),
            'group_dir':group_dir,
            'user_folder_data':user_folder_data,
            'parent_folder':parent_folder,
            "folder_id":current_group.root_id,
            'event_list_today':event_list_today,
            'event_list_other':event_list_other
        }
        return render(request, 'uth_groups_app/authenticated/groups/group_member.html',context)
    else:
        join_request_sended = False
        for student in current_group.join_requests.all():
            if current_student == student:
                join_request_sended = True
                break
        context = {
            "request":request,
            "course":course,
            'mygroups':mygroups,
            'selected_tab':selected_tab,
            'current_group':current_group,
            'join_request_sended':join_request_sended,
            'participants':participants,
            'owner':owner,
            'current_student':current_student
        }
        return render(request, 'uth_groups_app/authenticated/groups/group_not_member.html',context)

@login_required(login_url='home')
@is_student
def send_message(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    
    if request.method == 'POST':
        message = request.POST.get('message',False)
        course_pk = request.POST.get('course_pk',False)
        group_pk = request.POST.get('group_pk',False)

        if course_pk != False:
            item = Course.objects.get(pk=course_pk)
        else:
            item = Group.objects.get(pk=group_pk)
        
        sended_message = Message.objects.create(student=current_student,message=message)
        item.chat_messages.add(sended_message)
        context = {"chat_messages":item.chat_messages.all()}
        return render(request, 'uth_groups_app/authenticated/groups/renderchat.html',context)

def refresh_chat(request):
    course_pk = request.GET.get('course_pk',False)
    group_pk = request.GET.get('group_pk',False)
    if course_pk != False:
        try:
            item = Course.objects.get(pk=course_pk)
        except:
            item = None
    else:
        try:
            item = Group.objects.get(pk=group_pk)
        except:
            item = None
    if item == None:
        context = {"chat_messages":item}
    else:
        context = {"chat_messages":item.chat_messages.all()}
    return render(request, 'uth_groups_app/authenticated/groups/refreshchat.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_join_request(request):
    #accept or decline request
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    status = request.GET.get('status',False)
    course_pk = request.GET.get('team',False)
    if requester_id == False or status == False or course_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    course = Course.objects.get(pk=course_pk)
    if status=="Accept":
        join_team(requester_student.user,course)
        add_attendee_to_events(requester_student.user,course)
        course.join_requests.remove(requester_student)
        course.save()
    else:
        course.join_requests.remove(requester_student)
        course.save()
    course = Course.objects.get(pk=course_pk)
    admins = course.admins.all()
    context = {
        'participants': course.participants.all(),
        'join_request':course.join_requests.all(),
        'admins':admins,
        'course':course
    }
    return render(request, 'uth_groups_app/authenticated/courses/member_team_changes.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_kick_user(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    course_pk = request.GET.get('team',False)
    logger = logging.getLogger("mylogger")
    if requester_id == False or course_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    course = Course.objects.get(pk=course_pk)
    leave_team(requester_student.user,course)
    course = Course.objects.get(pk=course_pk)
    admins = course.admins.all()
    context = {
        'participants': course.participants.all(),
        'join_requests':course.join_requests.all(),
        'admins':admins,
        'course':course
    }
    return render(request, 'uth_groups_app/authenticated/courses/member_team_changes.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_remove_admin_request(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    course_pk = request.GET.get('team',False)
    if requester_id == False or course_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    course = Course.objects.get(pk=course_pk)
    course.admins.remove(requester_student)
    admins = course.admins.all()
    context = {
        'participants': course.participants.all(),
        'join_requests':course.join_requests.all(),
        'admins':admins,
        'course':course
    }
    return render(request, 'uth_groups_app/authenticated/courses/member_team_changes.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_make_admin_user(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    course_pk = request.GET.get('team',False)
    if requester_id == False or course_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    course = Course.objects.get(pk=course_pk)
    if requester_student not in course.admins.all():
        course.admins.add(requester_student)
    admins = course.admins.all()
    context = {
        'participants': course.participants.all(),
        'join_requests':course.join_requests.all(),
        'admins':admins,
        'course':course
    }
    return render(request, 'uth_groups_app/authenticated/courses/member_team_changes.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_join_request_group(request):
    #accept or decline request
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    status = request.GET.get('status',False)
    group_pk = request.GET.get('group',False)
    logger = logging.getLogger("mylogger")
    if requester_id == False or status == False or group_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    group = Group.objects.get(pk=group_pk)
    if status=="Accept":
        join_group(requester_student.user,group)
        add_attendee_to_events(requester_student.user,group.course,group)
        group.join_requests.remove(requester_student)
        group.save()
    else:
        group.join_requests.remove(requester_student)
        group.save()
    group = Group.objects.get(pk=group_pk)
    admins = group.admins.all()
    context = {
        'participants': group.participants.all(),
        'join_requests':group.join_requests.all(),
        'admins':admins,
        'current_group':group
    }
    return render(request, 'uth_groups_app/authenticated/groups/member_group_changes.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_kick_user_group(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    group_pk = request.GET.get('group',False)
    if requester_id == False or group_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    group = Group.objects.get(pk=group_pk)
    leave_group(requester_student.user,group)
    group = Group.objects.get(pk=group_pk)
    admins = group.admins.all()
    context = {
        'participants': group.participants.all(),
        'join_requests':group.join_requests.all(),
        'admins':admins,
        'current_group':group
    }
    return render(request, 'uth_groups_app/authenticated/groups/member_group_changes.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_remove_admin_request_group(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    group_pk = request.GET.get('group',False)
    if requester_id == False or group_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    group = Group.objects.get(pk=group_pk)
    group.admins.remove(requester_student)
    admins = group.admins.all()
    context = {
        'participants': group.participants.all(),
        'join_requests':group.join_requests.all(),
        'admins':admins,
        'current_group':group
    }
    return render(request, 'uth_groups_app/authenticated/groups/member_group_changes.html',context)

@login_required(login_url='home')
@is_admin_or_owner
def handle_make_admin_user_group(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    requester_id = request.GET.get('requester_id',False)
    group_pk = request.GET.get('group',False)
    if requester_id == False or group_pk==False:
        return HttpResponse('')
    requester_student = Student.objects.get(pk=requester_id)
    group = Group.objects.get(pk=group_pk)
    if requester_student not in group.admins.all():
        group.admins.add(requester_student)
    admins = group.admins.all()
    context = {
        'participants': group.participants.all(),
        'join_requests':group.join_requests.all(),
        'admins':admins,
        'current_group':group
    }
    return render(request, 'uth_groups_app/authenticated/groups/member_group_changes.html',context)
#REWORK
@login_required(login_url='home')
@is_student
def add(request):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    logger = logging.getLogger("mylogger")
    if request.method == 'POST':
        code = request.POST.get('code',False)
        if code == False:
            return render(request, 'uth_groups_app/authenticated/courses/add.html')
        try:
            course = Course.objects.get(code=code)
            if (course.owner == current_student) or (current_student in course.participants.all()):
                url = "/course/" + str(course.pk)
                return redirect(url)
            join_team(current_user,course)
            add_attendee_to_events(current_user,course)
            url = "/course/" + str(course.pk)
            return redirect(url)
        except Course.DoesNotExist:
            try:
                group = Group.objects.get(code=code)
                course = group.course
                if (group.owner == current_student) or (current_student in group.participants.all()):
                    url = "/course/" + str(course.pk) + "/group/" + str(group.pk)
                    return redirect(url)
                if (course.owner == current_student) or (current_student in course.participants.all()):
                    join_group(current_user,group)
                    add_attendee_to_events(current_user,course,group)
                else:
                    join_team(current_user,course)
                    join_group(current_user,group)
                    add_attendee_to_events(current_user,course)
                    add_attendee_to_events(current_user,course,group)
                url = "/course/" + str(course.pk) + "/group/" + str(group.pk)
                return redirect(url)
            except Group.DoesNotExist:
                err = "Δεν υπάρχει ομάδα ή group που να αντιστοιχεί σε αυτόν τον κωδικό."
                context = {'err':err}
                return render(request, 'uth_groups_app/authenticated/courses/add.html',context)

    return render(request, 'uth_groups_app/authenticated/courses/add.html')

@login_required(login_url='home')
@is_student
def createam(request):
    if request.method == 'POST':
        team_name = request.POST.get('team_name',False)
        team_description = request.POST.get('description',False)
        private = request.POST.get('private',False)
        if (private == "on"):
            private = True
        team_data = {
        'team_name': team_name,
        'description': team_description,
        'private': private,
        }
        state = create_team(request.user,team_data)
        if state == None:
            context = {"temp_teamname":team_name,"temp_team_description":team_description,"error_message":"Κάτι πήγε στραβά 😥."}
            return render(request, 'uth_groups_app/authenticated/courses/createam.html',context)
        
        return HttpResponseRedirect('/dashboard')

        
    return render(request, 'uth_groups_app/authenticated/courses/createam.html')

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
def deletefilefolder(request,folderID=None):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    if folderID == None:
        folder_id = request.GET['folder_id']
    else:
        folder_id = folderID
    filefolder_id_to_delete = request.GET.get('filefolder_id',False)
    owner_email = request.GET.get('owner_email',False)
    if filefolder_id_to_delete == False or owner_email== False:
        user_folder_data,parent_folder = folder_data(current_user,folder_id)
        if user_folder_data != None:
            user_folder_data = user_folder_data['files']
        context = {"request":request,'selected_tab':-1,"user_folder_data":user_folder_data,"parent_folder":parent_folder,"folder_id":folder_id}
        return render(request, 'uth_groups_app/authenticated/files/renderfiles.html',context)
    else:
        owneruser = User.objects.get(email=owner_email)
        deletefilefolder_drive(owneruser,filefolder_id_to_delete)
        user_folder_data,parent_folder = folder_data(current_user,folder_id)
        if user_folder_data != None:
            user_folder_data = user_folder_data['files']
        context = {"request":request,'selected_tab':-1,"user_folder_data":user_folder_data,"parent_folder":parent_folder,"folder_id":folder_id}
        return render(request, 'uth_groups_app/authenticated/files/renderfiles.html',context)
    

#CALENDAR FUCNTIONS
@login_required(login_url='home')
@is_student
@is_course_group_admin
def new_meet(request,course_id,group_id = None):
    current_user = request.user
    current_student = Student.objects.get(user=current_user)
    course = Course.objects.get(id=course_id)
    if group_id != None:
        group = Group.objects.get(id=group_id)

    mygroups = Group.objects.filter(course=course)

    if request.method == 'POST':
        logger = logging.getLogger("mylogger")
        meet_title = request.POST.get('meet_title',False)
        meet_desc = request.POST.get('meet_desc',False)
        instantCall = request.POST.get('instantCall',False)
        repeat_meet = request.POST.get('repeat_meet',False)
        repeat_times = request.POST.get('repeat_times',False)
        

        if instantCall == 'on':
            meeting_details = {
                "start": "now",
                "end" : "now",
                "meet_title" : meet_title,
                "meet_desc" : meet_desc,
                "repeat_meet" : "Δεν Επαναλαμβάνεται",
                "repeat_times" : None,
                "course_id" : course_id,
                "group_id" : group_id
                
            }
            state = create_event(current_user,meeting_details)
        else:
            start_datetime = request.POST.get('start_datetime',False)
            end_datetime = request.POST.get('end_datetime',False)

            start_datetime = datetime(*[int(v) for v in start_datetime.replace('T', '-').replace(':', '-').split('-')])
            end_datetime = datetime(*[int(v) for v in end_datetime.replace('T', '-').replace(':', '-').split('-')])

            difference = (end_datetime - start_datetime).total_seconds()

            if difference < 0:
                if group_id == None:
                    url = '/course/' + course_id + '/new-meet/'
                else:
                    url = '/course/' + course_id + '/group/'+ group_id + '/new-meet/'
                messages.error(request, 'Η ημερομηνία και ώρα που τελειώνει η συνάντηση δεν μπορεί να είναι πριν απο την έναρξη της.')
                return HttpResponseRedirect(url)
                

            meeting_details = {
                "start": start_datetime,
                "end" : end_datetime,
                "meet_title" : meet_title,
                "meet_desc" : meet_desc,
                "repeat_meet" : repeat_meet,
                "repeat_times" : repeat_times,
                "course_id" : course_id,
                "group_id" : group_id
            }
            state = create_event(current_user,meeting_details)

        return HttpResponseRedirect("/calendar")
    
    if group_id == None:
        context = {"request":request,'selected_tab':-2,"course":course,"mygroups":mygroups}
    else:
        context = {"request":request,'selected_tab':-2,"course":course,"group":group,"mygroups":mygroups}
    return render(request, 'uth_groups_app/authenticated/groups/new_meet.html',context)

