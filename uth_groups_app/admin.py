from django.contrib import admin
from .models import *


admin.site.register(Student)
admin.site.register(Course)
admin.site.register(Group)
admin.site.register(Course_root_folders_ids)
admin.site.register(Group_root_folders_ids)
admin.site.register(Uploader)
admin.site.register(UploadedFile)
admin.site.register(GoogleEvent)
admin.site.register(Message)