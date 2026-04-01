from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Redirige la racine vers la page de connexion (correspond à settings.LOGIN_URL)
    path('', RedirectView.as_view(pattern_name='dashboard:login', permanent=False)),

    # Page de connexion
    path('login/', views.DashboardLoginView.as_view(), name='login'),

    # Landing marketing optionnelle
    path('landing/', views.landing, name='landing'),
    
    # Vue principale du tableau de bord (après connexion)
    path('dashboard/', views.dashboard_index, name='dashboard_index'),
    path('logout/', views.DashboardLogoutView.as_view(), name='logout'),
    path('chat/', views.chat_with_gemini, name='chat_with_gemini'),
    path('notify-email/<int:pk>/', views.send_incident_email, name='send_incident_email'),
    
    # Generic incident list
    path('incidents/', views.incident_list, name='incident_list'),
    path('incidents/<str:category>/', views.incident_list, name='incident_list_category'),
    
    path('technicians/', views.technician_list, name='technician_list'),
    path('add-technician/', views.add_technician, name='add_technician'),
    path('edit-technician/<int:pk>/', views.edit_technician, name='edit_technician'),
    path('delete-technician/<int:pk>/', views.delete_technician, name='delete_technician'),
    path('analytics/', views.analytics_view, name='analytics_view'),
    path('manage-users/', views.user_management, name='user_management'),
    path('add-user/', views.add_user, name='add_user'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('update-incident/<int:pk>/', views.update_incident, name='update_incident'),
    path('export-csv/', views.export_incidents_csv, name='export_incidents_csv'),
    path('report/', views.report_incident, name='report_incident'),
    path('my-incidents/', views.user_incidents_view, name='user_incidents'),
    path('profile/', views.profile_view, name='profile_view'),
    path('api/analyze-incident/', views.analyze_incident_api, name='analyze_incident_api'),
    path('api/transcribe/', views.transcribe_audio, name='transcribe_audio'),
    path('register/', views.register_view, name='register'),
    path('incident/<int:pk>/', views.incident_detail, name='incident_detail'),
    path('api/user-dashboard/', views.user_dashboard_api, name='user_dashboard_api'),
    path('api/latest-incidents/', views.latest_incidents_api, name='latest_incidents_api'),
    
    # Telegram Integration
    path('telegram/webhook/', views.telegram_webhook, name='telegram_webhook'),
    path('telegram/link/<str:token>/', views.telegram_link_confirm, name='telegram_link_confirm'),
    path('link-telegram/', views.telegram_link_page, name='link_telegram'),
    
    # Registration
    path('register/', views.RegisterView.as_view(), name='register'),
]

from django.contrib.auth import views as auth_views

# Authentication (OTP flow)
urlpatterns += [
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/new/', views.password_reset_new, name='password_reset_new'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='dashboard/password_reset_complete.html'), name='password_reset_complete'),
]
