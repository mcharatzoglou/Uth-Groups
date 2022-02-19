from django import forms
from django.db import models
from django.db.models import fields
from .models import *

class UploadFileForm(forms.Form):
    files = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))
