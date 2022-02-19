from string import Template
from django.http import HttpResponse , HttpResponseRedirect 
from django.shortcuts import redirect
from .models import *
import logging



def unauthenticated_user(view_func):
    def wrapper_func(request,*args,**kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        else:
            return view_func(request,*args, **kwargs)
    return wrapper_func

def is_student(view_func):
    def wrapper_func(request,*args,**kwargs):
        try:
            current_student = Student.objects.get(user=request.user)
            if current_student.is_academic_authorized == False:
                current_student = None
        except Student.DoesNotExist:
            current_student = None
        if current_student == None:
            return redirect('new')
        else:
            return view_func(request,*args, **kwargs)
    return wrapper_func

def is_uploader(view_func):
    def wrapper_func(request,*args,**kwargs):
        try:
            current_uploader = Uploader.objects.get(user=request.user)
        except Uploader.DoesNotExist:
            current_uploader = None
        if current_uploader == None:
            return redirect('new')
        else:
            return view_func(request,*args, **kwargs)
    return wrapper_func

def is_course_valid(view_func):
    def wrapper_func(request,*args,**kwargs):
        try:
            pk = kwargs.get('course_id')
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return redirect('dashboard')
        return view_func(request,*args, **kwargs)
    return wrapper_func

def is_course_member(view_func):
    def wrapper_func(request,*args,**kwargs):
        try:
            pk = kwargs.get('course_id')
            student = Student.objects.get(user=request.user)
            course = Course.objects.get(participants=student,pk=pk)
        except Course.DoesNotExist:
            try:
                course = Course.objects.get(owner=student,pk=pk)
            except Course.DoesNotExist:
                course = None
        if course == None:
            return redirect('dashboard')
        else:
            return view_func(request,*args, **kwargs)
    return wrapper_func

def is_group_valid(view_func):
    def wrapper_func(request,*args,**kwargs):
        student = Student.objects.get(user=request.user)
        course_id = kwargs.get('course_id')
        try:
            course = Course.objects.get(participants=student,id=course_id)
        except Course.DoesNotExist:
            try:
                course = Course.objects.get(owner=student,id=course_id)
            except Course.DoesNotExist:
                return redirect('dashboard')

        try:
            pk = kwargs.get('group_id')
            group = Group.objects.get(course=course,pk=pk)
        except:
            return redirect('dashboard')
        try:
            group = Group.objects.get(participants=student,pk=pk)
        except Group.DoesNotExist:
            group = None
        
        if group == None:
            try:
                group = Group.objects.get(owner=student,pk=pk)
            except Group.DoesNotExist:
                group = None

        return view_func(request,*args, **kwargs)
    return wrapper_func


def is_course_group_owner(view_func):
    def wrapper_func(request,*args,**kwargs):
        student = Student.objects.get(user=request.user)
        course_id = kwargs.get('course_id')
        group_id = kwargs.get('group_id')

        if group_id == None:
            try:
                course = Course.objects.get(owner=student,id=course_id)
                return view_func(request,*args, **kwargs)
            except Course.DoesNotExist:
                return redirect('dashboard')
        
        try:
            group = Group.objects.get(owner=student,pk=group_id)
            return view_func(request,*args, **kwargs)
        except Group.DoesNotExist:
            return redirect('dashboard')
            
    return wrapper_func

def is_course_group_admin(view_func):
    def wrapper_func(request,*args,**kwargs):
        student = Student.objects.get(user=request.user)
        course_id = kwargs.get('course_id')
        group_id = kwargs.get('group_id')
        logger = logging.getLogger("mylogger")

        if group_id == None:
            try:
                course = Course.objects.get(admins=student,id=course_id)
                return view_func(request,*args, **kwargs)
            except Course.DoesNotExist:
                try:
                    course = Course.objects.get(owner=student,id=course_id)
                    return view_func(request,*args, **kwargs)
                except:
                    return redirect('dashboard')
        
        try:
            group = Group.objects.get(admins=student,pk=group_id)
            return view_func(request,*args, **kwargs)
        except Group.DoesNotExist:
            try:
                group = Group.objects.get(owner=student,pk=group_id)
                return view_func(request,*args, **kwargs)
            except:
                return redirect('dashboard')
            
    return wrapper_func

def is_admin_or_owner(view_func):
    def wrapper_func(request,*args,**kwargs):
        student = Student.objects.get(user=request.user)
        course_pk = request.GET.get('team',False)
        group_pk = request.GET.get('group',False)

        if group_pk == False:
            item = Course.objects.get(pk=course_pk)
        else:
            item = Group.objects.get(pk=group_pk)

        if student in item.admins.all() or student == item.owner:
            return view_func(request,*args, **kwargs)
        
        return HttpResponse('Δεν είστε πλέον διαχειριστής.')
    return wrapper_func