from django.urls import path
from . import views
from django.conf.urls import handler404
from django.conf import settings
# from .views import student_message, SendMessageView, GetMessagesView 
urlpatterns=[
    path('', views.home, name='home'),
    path('aboutus/', views.aboutus, name='aboutus'),
    path('bonbon/<str:user_id>/', views.pp, name='pp'),
    path('ownersRoomManagement/update/', views.update_room, name='update_room'),
    #Messages/Chats 
    # path('send-message/', SendMessageView.as_view(), name='send_message'),  # Add the send message route
    # path('get-messages/<str:superadmin_email>/<str:user_email>/', GetMessagesView.as_view(), name='get_messages'),  # Add get messages route
 

    #Users complain
    path('owner/owner_login/owner_report_problem', views.owner_report_problem, name='owner_report_problem'),
    path('student/student_login/student_report_problem', views.student_report_problem, name='student_report_problem'),
    path('sao/saofeedback/student_report', views.student_report, name='student_report'),
    path('sao/saofeedback/owner_report', views.owner_report, name='owner_report'),

    #This is for SAO
    path('sao/sao_login/', views.sao_login, name='sao_login'),
    path('sao/saohomepage/', views.saohomepage, name='saohomepage'),
    path('sao/saohomepage/sao_message/', views.sao_message, name='sao_message'), 
    path('sao/saohomepage/sao_message/sao_delete_conversation/<str:student_email>/', views.sao_delete_conversation, name='sao_delete_conversation'),
    path('sao/saohomepage/message_sao_owner/', views.message_sao_owner, name='message_sao_owner'), 
    path('sao/saohomepage/message_sao_owner/delete_conversation_by_sao_owner/<str:owner_email>/', views.delete_conversation_by_sao_owner, name='delete_conversation_by_sao_owner'),
     
    path('update_days_login_sao/', views.update_days_login_sao, name='update_days_login_sao'),
    path('sao/usermonitoring', views.usermonitoring, name='usermonitoring'), 
    
    path('sao/sao_feedback/', views.sao_feedback, name='sao_feedback'),
    path('sao/sao_settings/', views.sao_settings, name='sao_settings'),
    path('sao/saohomepage/pendingreq/', views.pendingreq, name='pendingreq'),
    path('sao/saohomepage/demoAddStudent/', views.demoAddStudent, name='demoAddStudent'),
    path('sao/saohomepage/demoAddSAO/', views.demoAddSAO, name='demoAddSAO'),
     
    path('sao/saohomepage/pendingreq/boardinghouseAction', views.boardinghouseAction, name='boardinghouseAction'),
    path('sao/saohomepage/add_student/', views.add_student, name='add_student'),
    path('sao/saohomepage/addsuperadmin/', views.addsuperadmin, name='addsuperadmin'),
    path('sao/saohomepage/view_students/', views.view_students, name='view_students'),
    path('sao/saohomepage/view_owners/', views.view_owners, name='view_owners'),
    path('sao/saohomepage/view_owners/view_owners_boarding_house', views.view_owners_boarding_house, name='view_owners_boarding_house'),
    path('sao/sao_forgotpassword/', views.sao_forgotpassword, name='sao_forgotpassword'),
    path('sao/sao_login/sao_verify_otp/', views.sao_verify_otp, name='sao_verify_otp'),
    path('sao/generatingReports/', views.generatingReports, name='generatingReports'),
    path('sao/generateStudentReports/', views.generateStudentReports, name='generateStudentReports'), 
     
    path('saologout/', views.saologout, name='saologout'),
    path('download_csv/', views.download_csv, name='download_csv'),
    
    path('undoactions/rejectstudents', views.rejectstudents, name='rejectstudents'),
    path('undoactions/rejectowners', views.rejectowners, name='rejectowners'),
    path('undoactions/disablestudents', views.disablestudents, name='disablestudents'),
    path('undoactions/disableowners', views.disableowners, name='disableowners'),
    path('undoactions/removestudents', views.removestudents, name='removestudents'),
    path('undoactions/removeowners', views.removeowners, name='removeowners'),
    path('undoactions/removesao', views.removesao, name='removesao'),
     
     
    #This is for Owner
    path('owner/owner_login/', views.owner_login, name='owner_login'),
    path('owner/owner_login/ownerSignUpFirstStep/', views.ownerSignUpFirstStep, name='ownerSignUpFirstStep'),
    path('owner/ownerhomepage/ownerSignUpSecondStep/', views.ownerSignUpSecondStep, name='ownerSignUpSecondStep'),
    path('ownerSignUpThirdStep/', views.ownerSignUpThirdStep, name='ownerSignUpThirdStep'),
    path('ownerSignUpFourthStep/', views.ownerSignUpFourthStep, name='ownerSignUpFourthStep'),
    path('owner/ownerhomepage/', views.ownerhomepage, name='ownerhomepage'),
    path('owner/ownerhomepage/message_owner', views.message_owner, name='message_owner'),
    path('owner/ownerhomepage/message_owner/delete_conversationOwner/<str:superadmin_email>/', views.delete_conversationOwner, name='delete_conversationOwner'),
    path('owner/ownerhomepage/owner_message_students', views.owner_message_students, name='owner_message_students'),
    path('owner/ownerhomepage/owner_message_students/delete_conversation_by_owner_student/<str:student_email>/', views.delete_conversation_by_owner_student, name='delete_conversation_by_owner_student'),
    
    path("owner/ownerhomepage/ownerSignUpSecondStep/view_images/", views.view_images, name="view_images"),
    

    path("owner/ownerhomepage/ownerSignUpSecondStep/location/", views.location_form, name="location_form"),
    path("save-location/", views.save_location, name="save_location"),


    path('owner/ownerhomepage/ownersRoomManagement', views.ownersRoomManagement, name='ownersRoomManagement'),
    path('owner/ownerhomepage/ownersTenantsManagement', views.ownersTenantsManagement, name='ownersTenantsManagement'),
    path('owner/ownerlodger/', views.ownerlodger, name='ownerlodger'),
    path('owner/ownerfeedback/', views.ownerfeedback, name='ownerfeedback'),
    path('owner/ownersettings/', views.ownersettings, name='ownersettings'),
    path('owner/owner_login/ownerSignUpFirstStep/ownerVerifyOtp/', views.ownerVerifyOtp, name='ownerVerifyOtp'),
    path('owner/owner_forgotpassword/', views.owner_forgotpassword, name='owner_forgotpassword'),
    path('ownerlogout/', views.ownerlogout, name='ownerlogout'),
    path('owner/ownerhomepage/owner_homeReport', views.owner_homeReport, name='owner_homeReport'),
    
    path('update_days_login_owner/', views.update_days_login_owner, name='update_days_login_owner'),
  
    #This is for Student
    path('student/student_login/', views.student_login, name='student_login'),
    path('student/student_login/studentSignupFirststep/', views.studentSignupFirststep, name='studentSignupFirststep'),
    path('studentSignupSecondstep/', views.studentSignupSecondstep, name='studentSignupSecondstep'),
    path('studentProfilePicture/', views.studentProfilePicture, name='studentProfilePicture'), 
    path('studentbase/', views.studentbase, name='studentbase'),
    path('student/studenthomepage/', views.studenthomepage, name='studenthomepage'),
    path('student/studenthomepage/student_apply_now', views.student_apply_now, name='student_apply_now'),
    path('student/studenthomepage/student_apply_now/trackLocation', views.trackLocation, name='trackLocation'),
    path('student/studenthomepage/student_message', views.student_message, name='student_message'),
    path('student/studenthomepage/student_message/delete_conversation/<str:superadmin_email>/', views.delete_conversation, name='delete_conversation'),
    path('student/studenthomepage/owner_message', views.owner_message, name='owner_message'),
    path('student/studenthomepage/owner_message/delete_conversation_by_owner/<str:owner_email>/', views.delete_conversation_by_owner, name='delete_conversation_by_owner'),
    path('student/studenthomepage/student_homeReport', views.student_homeReport, name='student_homeReport'),
    
    path('update_days_login/', views.update_days_login, name='update_days_login'),
 
    path('student/studentapplication/', views.studentapplication, name='studentapplication'),
    path('student/studentsettings/', views.studentsettings, name='studentsettings'),
    # path('student/studentmessage/', views.studentmessage, name='studentmessage'),
    path('student/studentnotification/', views.studentnotification, name='studentnotification'),
    path('studentlogout/', views.studentlogout, name='studentlogout'),
    path('student/student_login/studentSignupFirststep/studentverify/', views.studentverify, name='studentverify'),
    path('student/student_forgotpassword/', views.student_forgotpassword, name='student_forgotpassword'),
]  
handler404 = 'DataLink_Django.views.custom_404'
