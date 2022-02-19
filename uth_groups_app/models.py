from operator import mod
from django.db import models
from django.contrib.auth.models import User

import os
import uuid

from django.db import models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

class Student(models.Model):
    user = models.OneToOneField(User,null=True,on_delete=models.CASCADE)
    description = models.CharField(max_length=2000,default="",blank=True,null=True)
    root_folder_id = models.CharField(max_length=200,default="",blank=True,null=True)
    calendar_id = models.CharField(max_length=200,default="",blank=True,null=True)
    is_academic_authorized = models.BooleanField(default=False)
    academic_email = models.CharField(max_length=200,default=None,blank=True,null=True)
    authorization_code = models.CharField(max_length=200,default=None,blank=True,null=True)
    def __str__(self):
        return (self.user.first_name + " " + self.user.last_name)

class Message(models.Model):
    student = models.ForeignKey(Student,on_delete=models.CASCADE)
    message = models.CharField(max_length=2000,default="",blank=True,null=True)
    sended_at = models.DateTimeField(auto_now_add=True)

class Course(models.Model):
    owner = models.ForeignKey(Student,related_name='TeamOwner',on_delete=models.CASCADE,null=True)
    course_name = models.CharField(max_length=200)
    participants = models.ManyToManyField(Student,related_name='Participants')
    join_requests = models.ManyToManyField(Student,related_name='CourseJoinRequests')
    admins = models.ManyToManyField(Student,related_name='CourseAdmins')
    chat_messages = models.ManyToManyField(Message,related_name='ChatMessages')
    private = models.BooleanField(default=False)
    datetime = models.CharField(max_length=200,default=" ")
    folder_id = models.CharField(max_length=200,null=True)
    files_folder_id = models.CharField(max_length=200,null=True)
    code = models.CharField(max_length=200,null=True,default=None) 
    def __str__(self):
        return self.course_name

class Group(models.Model):
    owner = models.ForeignKey(Student,related_name='Owner',on_delete=models.CASCADE)
    title = models.CharField(max_length=200,null=True)
    datetime = models.CharField(max_length=200,default=" ")
    description = models.TextField(max_length=2000,blank=True)
    course = models.ForeignKey(Course,on_delete=models.CASCADE) #from student courses
    private = models.BooleanField(default=False)
    participants = models.ManyToManyField(Student)
    join_requests = models.ManyToManyField(Student,related_name='GroupJoinRequests')
    admins = models.ManyToManyField(Student,related_name='GroupAdmins')
    chat_messages = models.ManyToManyField(Message,related_name='ChatMessagesGroup')
    root_id = models.CharField(max_length=200,null=True)
    code = models.CharField(max_length=200,null=True,default=None)
    def __str__(self):
        return (self.title)


class Course_root_folders_ids(models.Model):
    student = models.ForeignKey(Student,on_delete=models.CASCADE)
    course = models.ForeignKey(Course,on_delete=models.CASCADE)
    root_id = models.CharField(max_length=200,null=True)
    root_files_id = models.CharField(max_length=200,null=True)
    root_groups = models.CharField(max_length=200,null=True)
    def __str__(self):
        return self.root_id

class Group_root_folders_ids(models.Model):
    student = models.ForeignKey(Student,on_delete=models.CASCADE)
    group = models.ForeignKey(Group,on_delete=models.CASCADE,null=True)
    root_id = models.CharField(max_length=200,null=True)
    shorcut_id = models.CharField(max_length=200,null=True)
    def __str__(self):
        return self.root_id

class Uploader(models.Model):
    user = models.OneToOneField(User,null=True,on_delete=models.CASCADE)
    total_space = models.BigIntegerField(default=0)
    used_space = models.BigIntegerField(default=0)
    available_space = models.BigIntegerField(default=0)
    total_space_str = models.CharField(max_length=200,default=0)
    used_space_str = models.CharField(max_length=200,default=0)
    available_space_str = models.CharField(max_length=200,default=0)
    base_id = models.CharField(max_length=200,default=0)
    shorcut_id = models.CharField(max_length=200,default=0)
    active = models.BooleanField(default=False)
    def __str__(self):
        return (self.user.email)

class UploadedFile(models.Model):
    student = models.ForeignKey(Student,on_delete=models.CASCADE)
    course = models.ForeignKey(Course,on_delete=models.CASCADE,null=True,default=None)
    group = models.ForeignKey(Group,on_delete=models.CASCADE,null=True,default=None)
    folder_id = models.CharField(max_length=200,null=True)
    filename = models.CharField(max_length=200,null=True)
    file = models.FileField()


class GoogleEvent(models.Model):
    iCalUID = models.CharField(max_length=200,null=True)
    owner = models.ForeignKey(Student,on_delete=models.CASCADE,related_name='EventOwner',null=True,default=None)
    participants = models.ManyToManyField(Student)
    course = models.ForeignKey(Course,on_delete=models.CASCADE,null=True,default=None)
    group = models.ForeignKey(Group,on_delete=models.CASCADE,null=True,default=None)





@receiver(models.signals.post_delete, sender=UploadedFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

