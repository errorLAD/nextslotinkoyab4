"""
URL configuration for accounts app.
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import views_client

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Registration
    path('register/', views.register_choice_view, name='register_choice'),
    path('register/provider/', views.register_provider_view, name='register_provider'),
    path('register/client/', views.register_client_view, name='register_client'),
    
    # Client Dashboard & Booking History
    path('dashboard/', views_client.client_dashboard, name='client_dashboard'),
    path('appointment/<int:pk>/', views_client.appointment_detail_client, name='appointment_detail_client'),
    path('appointment/<int:pk>/cancel/', views_client.cancel_appointment_client, name='cancel_appointment_client'),
    path('appointment/<int:pk>/reschedule/', views_client.reschedule_appointment_client, name='reschedule_appointment_client'),
    path('appointment/<int:pk>/rebook/', views_client.rebook_appointment, name='rebook_appointment'),
    path('favorites/', views_client.favorite_providers_list, name='favorite_providers'),
    path('favorites/add/<int:provider_id>/', views_client.add_favorite_provider, name='add_favorite_provider'),
    path('favorites/remove/<int:provider_id>/', views_client.remove_favorite_provider, name='remove_favorite_provider'),
    path('notifications/', views_client.notification_preferences, name='notification_preferences'),
    
    # Email Verification
    path('verification-sent/', views.verification_sent_view, name='verification_sent'),
    path('verify-email/<int:user_id>/<str:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    
    # Password Reset (using Django's built-in views)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.txt',
             html_email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/accounts/password-reset/done/'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
