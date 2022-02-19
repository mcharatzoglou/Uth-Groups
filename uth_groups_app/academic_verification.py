import smtplib, ssl
from .models import *
import requests
from bs4 import BeautifulSoup
import logging


#verify gmail
def send_verification_email(user):
    current_student = Student.objects.get(user=user)
    port = 587  # For starttls
    smtp_server = "smtp.gmail.com"
    sender_email = "uthgroups.noreply@gmail.com"
    receiver_email = current_student.academic_email
    password = "PASSWORD_HERE"
    SUBJECT = "Uth Groups - Academic account verification "
    TEXT = "Dear "+ str(current_student) + ", your OTP for registration is : " + current_student.authorization_code + "\n\n Uth Groups"
    message = 'From: Uth Groups\nSubject: {}\n\n{}'.format(SUBJECT, TEXT).encode('utf8')

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)
    return 1

def retrieve_GRNET_academic_data(user):
    current_student = Student.objects.get(user=user)
    first_name = current_student.user.first_name
    last_name = current_student.user.last_name
    title = "-"
    payload = {'attribute': 'mail', 'criterion': '=', 'keyword' : current_student.academic_email , 'dn' : 'dc=uth,dc=gr' , 'search' : 'αναζήτηση'}
    r = requests.post("https://ds.grnet.gr", data=payload)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        try:
            first_name = soup.find_all(class_='given-name')[0].get_text()
            last_name =  soup.find_all(class_='family-name')[0].get_text()
            title = soup.find_all(class_='title')[1].get_text()
        except Exception:
            pass
    return first_name,last_name,title

