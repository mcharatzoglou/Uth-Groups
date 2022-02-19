from django.urls import path ,include
from django.conf.urls import url
from . import views

urlpatterns = [
    path('accounts/login/', views.index, name='home'),
    path('accounts/signup/', views.index, name='home'),
    path('accounts/password/set/', views.index, name='home'),
    path('accounts/inactive/', views.index, name='home'),
    path('accounts/email/', views.index, name='home'),
    path('accounts/confirm-email/', views.index, name='home'),
    path('accounts/social/', views.index, name='home'),
    path('accounts/google/', views.index, name='home'),
    url(r'accounts/social/', views.index, name='index'),
    url(r'accounts/password/', views.index, name='index'),

    
    path('', views.index, name='home'),
    path('privacy-policy/', views.privacypolicy, name='privacypolicy'),
    path('academicAuthorization/', views.academicAuthorization, name='academicAuthorization'),
    path('backAcademicAuthorization/', views.backAcademicAuthorization, name='backAcademicAuthorization'),
    path('cancelAcademicAuthorization/', views.cancelAcademicAuthorization, name='cancelAcademicAuthorization'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('calendar/', views.calendar, name='calendar'),
    path('profile/', views.profile, name='profile'),
    path('new/', views.new, name='new'),
    path('logout/', views.logout_user, name='logout_user'),
    path('groupsearch/', views.groupsearch, name='groupsearch'),
    path('add/', views.add, name='add'),
    path('add/create', views.createam, name='createam'),
    path('addcourse/', views.add_course, name='add-course'),
    path('course/<str:course_id>', views.coursePage, name='coursePage'),
    path('course/<slug:course_id>/newgroup/creategroup/', views.creategroup, name='creategroup'),
    path('course/<slug:course_id>/group/<slug:group_id>', views.groupPage, name='groupPage'),
    path('renderfolder/', views.renderfolder, name='renderfolder'),
    path('about/', views.about, name='about'),
    path('change/', views.change_private, name='private'),
    path('create-code/', views.create_code, name='create_code'),
    path('delete-code/', views.delete_code, name='delete_code'),
    path('team-change/', views.team_change_private, name='team_private'),
    path('team-members/', views.handle_join_request, name='handle_join_request'),
    path('kick-members/', views.handle_kick_user, name='handle_kick_user'),
    path('group-members/', views.handle_join_request_group, name='handle_join_request_group'),
    path('kick-group-members/', views.handle_kick_user_group, name='handle_kick_user_group'),
    path('kick-admin/', views.handle_remove_admin_request, name='handle_remove_admin_request'),
    path('make-admin/', views.handle_make_admin_user, name='handle_make_admin_user'),
    path('kick-admin-group/', views.handle_remove_admin_request_group, name='handle_remove_admin_request_group'),
    path('make-admin-group/', views.handle_make_admin_user_group, name='handle_make_admin_user_group'),
    path('team-create-code/', views.team_create_code, name='team_create_code'),
    path('team-delete-code/', views.team_delete_code, name='team_delete_code'),
    path('deletefilefolder/', views.deletefilefolder, name='deletefilefolder'),
    path('course/<slug:course_id>/new-meet/', views.new_meet, name='new_meet'),
    path('course/<slug:course_id>/group/<slug:group_id>/new-meet/', views.new_meet, name='new_meet'),
    path('send_message', views.send_message, name='send_message'),
    path('refresh_chat/', views.refresh_chat, name='refresh_chat'),
    
    
    
    

    #uploaders
    path('control/', views.control, name='control'),
    path('upload', views.upload_file, name='upload_file'),
    path('createfolder', views.create_folder, name='create_folder'),
    #path('control/initdrive', views.initdrive, name='initdrive')
]