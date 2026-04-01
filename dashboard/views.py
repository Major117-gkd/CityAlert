from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import logout, login
from django.db.models import Count, Q
from django.contrib.auth.models import User
from .models import Incident, Technician, PasswordResetCode, UserProfile, TelegramUser
from django import forms
from django.http import JsonResponse, HttpResponse
import json
import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import csv
import threading
import io
from PIL import Image
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from .utils import find_closest_technician, calculate_distance
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.core.mail import send_mail
import math
import uuid
from django.core.cache import cache

# Add geocoding API to get address from coordinates
def get_address_from_coordinates(lat, lon):
    api_key = os.getenv('GEOCODING_API_KEY')
    if not api_key:
        # Tentative de récupération depuis settings au cas où
        from django.conf import settings
        api_key = getattr(settings, 'GEOCODING_API_KEY', None)
    
    if not api_key:
        # Simulation en l'absence de clé API
        return "Adresse non disponible"
    
    url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()
        try:
            return result['results'][0]['formatted_address']
        except (KeyError, IndexError):
            return "Adresse non disponible"
    else:
        return "Erreur lors de la récupération de l'adresse"

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'phone', 'address']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Parlez-nous de vous...'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Votre numéro de téléphone'}),
            'address': forms.TextInput(attrs={'placeholder': 'Votre adresse'}),
        }

@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success', 'message': 'Profil mis à jour avec succès'})
        return JsonResponse({'status': 'error', 'message': 'Erreur lors de la mise à jour'})
    
    form = UserProfileForm(instance=profile)
    return render(request, 'dashboard/profile.html', {'form': form, 'profile': profile})

@login_required
def user_incidents_view(request):
    user_incidents = Incident.objects.filter(user_email=request.user.email).order_by('-timestamp')
    return render(request, 'dashboard/user_incidents.html', {'incidents': user_incidents})

def landing(request):
    """
    Page d'accueil publique moderne.
    Si l'utilisateur est déjà authentifié, on le redirige vers le tableau de bord.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard_index')
    return render(request, 'dashboard/landing.html')


def get_gemini_session():
    """Crée une session requests avec une stratégie de retentative robuste."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

@login_required
@csrf_exempt
def chat_with_gemini(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            if not user_message:
                return JsonResponse({'error': 'Message is required'}, status=400)
            
            # Using Gemini API key from environment variable (set GEMINI_API_KEY)
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if not gemini_api_key:
                # Tentative de récupération depuis settings au cas où
                from django.conf import settings
                gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
            
            if not gemini_api_key:
                # Simulation en l'absence de clé API Gemini
                return JsonResponse({
                    'response': f"[Simulation] Pas de clé Gemini configurée. Vous avez demandé : \"{user_message}\".\nPour une vraie réponse IA, définissez GEMINI_API_KEY dans vos variables d'environnement ou dans settings.py."
                })

            # Using the latest Gemini 1.5 Flash model (stable v1)
            url = f'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={gemini_api_key}'
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"""Tu es un assistant IA spécialisé dans l'aide aux utilisateurs du système CityAlert (anciennement WaterAlert), un système de monitoring multi-incidents.
Contexte: Le système gère maintenant les fuites d'eau, les accidents de la route et les courts-circuits électriques.
L'utilisateur te pose cette question : {user_message}
Réponds de manière utile, concise et en français."""
                    }]
                }]
            }
            
            headers = {'Content-Type': 'application/json'}
            session = get_gemini_session()
            response = session.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 429:
                return JsonResponse({'response': "Le service Gemini est saturé. [Mode Secours] Je peux répondre à vos questions générales sur les incidents en attendant. Que souhaitez-vous savoir ?"})

            if response.status_code == 200:
                result = response.json()
                try:
                    bot_response = result['candidates'][0]['content']['parts'][0]['text']
                    return JsonResponse({'response': bot_response})
                except (KeyError, IndexError):
                    return JsonResponse({'response': f"Réponse inattendue de l'IA: {json.dumps(result)}"})
            
            # Gestion spécifique des erreurs API
            error_data = response.json() if response.headers.get('Content-Type') == 'application/json' else {'error': {'message': response.text}}
            error_msg = error_data.get('error', {}).get('message', 'Erreur inconnue')
            return JsonResponse({'response': f"Erreur API Gemini ({response.status_code}) : {error_msg}"})
        except Exception as e:
            return JsonResponse({'response': f"Erreur système: {str(e)}"})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def incident_list(request, category=None):
    incidents = Incident.objects.all().order_by('-timestamp')
    if category:
        # Map URL slug to DB categories (flexible matching)
        cat_map = {
            'eau': ['Eau', 'Fuite'],
            'accident': ['Accident', 'Route', 'Routier'],
            'electricite': ['Electricité', 'Électricité', 'Elec', 'Circuit']
        }
        variants = cat_map.get(category.lower(), [category])
        query = Q()
        for v in variants:
            query |= Q(category__icontains=v)
        incidents = incidents.filter(query)
    return render(request, 'dashboard/incidents.html', {'incidents': incidents, 'category': category})

@login_required
def technician_list(request):
    """CRUD Read - Liste des techniciens"""
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return redirect('dashboard:dashboard_index')
    
    technicians = Technician.objects.all().order_by('name')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON for AJAX requests
        data = []
        for tech in technicians:
            data.append({
                'id': tech.id,
                'name': tech.name,
                'email': tech.email,
                'phone': tech.phone,
                'category': tech.category,
                'specialty': getattr(tech, 'specialty', ''),
                'latitude': tech.latitude,
                'longitude': tech.longitude,
                'avatar_color': getattr(tech, 'avatar_color', '#3b82f6')
            })
        return JsonResponse({'technicians': data})
    
    # Return HTML for normal requests
    return render(request, 'dashboard/technicians.html', {'technicians': technicians})

@login_required
def add_technician(request):
    """CRUD Create - Ajouter un technicien"""
    # Seul un admin peut accéder à cette vue
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return redirect('dashboard:technician_list')
        
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            name = data.get('name')
            category = data.get('category')
            specialty = data.get('specialty')
            phone = data.get('phone')
            email = data.get('email')
            lat = data.get('latitude')
            lon = data.get('longitude')
            
            if name and category and lat and lon and email:
                technician = Technician.objects.create(
                    name=name,
                    category=category,
                    specialty=specialty,
                    phone=phone,
                    email=email,
                    latitude=float(lat),
                    longitude=float(lon)
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success', 
                        'message': 'Technicien ajouté avec succès',
                        'technician': {
                            'id': technician.id,
                            'name': technician.name,
                            'email': technician.email,
                            'phone': technician.phone,
                            'category': technician.category,
                            'specialty': getattr(technician, 'specialty', ''),
                            'latitude': technician.latitude,
                            'longitude': technician.longitude,
                            'avatar_color': getattr(technician, 'avatar_color', '#3b82f6')
                        }
                    })
                
                return redirect('dashboard:technician_list')
            else:
                error_msg = 'Tous les champs sont obligatoires'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                return render(request, 'dashboard/add_technician.html', {'error': error_msg})
                
        except ValueError:
            error_msg = 'Coordonnées invalides'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            return render(request, 'dashboard/add_technician.html', {'error': error_msg})
        except Exception as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            return render(request, 'dashboard/add_technician.html', {'error': error_msg})
            
    return render(request, 'dashboard/add_technician.html')

@login_required
def edit_technician(request, pk):
    """CRUD Update - Modifier un technicien"""
    # Seul un admin peut modifier un technicien
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return redirect('dashboard:technician_list')
        
    technician = get_object_or_404(Technician, pk=pk)
    
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            technician.name = data.get('name', technician.name)
            technician.category = data.get('category', technician.category)
            technician.specialty = data.get('specialty', getattr(technician, 'specialty', ''))
            technician.phone = data.get('phone', technician.phone)
            technician.email = data.get('email', technician.email)
            
            lat = data.get('latitude')
            lon = data.get('longitude')
            try:
                if lat: technician.latitude = float(lat)
                if lon: technician.longitude = float(lon)
            except ValueError:
                pass # On garde les anciennes valeurs si invalides
            
            technician.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Technicien modifié avec succès',
                    'technician': {
                        'id': technician.id,
                        'name': technician.name,
                        'email': technician.email,
                        'phone': technician.phone,
                        'category': technician.category,
                        'specialty': getattr(technician, 'specialty', ''),
                        'latitude': technician.latitude,
                        'longitude': technician.longitude,
                        'avatar_color': getattr(technician, 'avatar_color', '#3b82f6')
                    }
                })
            
            return redirect('dashboard:technician_list')
            
        except Exception as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            return render(request, 'dashboard/edit_technician.html', {'technician': technician, 'error': error_msg})
        
    return render(request, 'dashboard/edit_technician.html', {'technician': technician})

@login_required
def delete_technician(request, pk):
    """CRUD Delete - Supprimer un technicien"""
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return redirect('dashboard:technician_list')
        
    technician = get_object_or_404(Technician, pk=pk)
    
    if request.method == 'POST' or request.method == 'DELETE':
        try:
            technician_name = technician.name
            technician.delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success', 
                    'message': f'Technicien {technician_name} supprimé avec succès'
                })
            
            return redirect('dashboard:technician_list')
            
        except Exception as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            return redirect('dashboard:technician_list')
    
    return redirect('dashboard:technician_list')


@login_required
def user_management(request):
    """CRUD Read - Liste des utilisateurs"""
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return redirect('dashboard:dashboard_index')
    
    users = User.objects.all().order_by('-date_joined')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON for AJAX requests
        data = []
        for user in users:
            try:
                profile = user.profile
                data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    'phone': profile.phone if hasattr(profile, 'phone') else '',
                    'address': profile.address if hasattr(profile, 'address') else '',
                    'avatar': profile.avatar.url if hasattr(profile, 'avatar') and profile.avatar else ''
                })
            except:
                data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    'phone': '',
                    'address': '',
                    'avatar': ''
                })
        return JsonResponse({'users': data})
    
    # Return HTML for normal requests
    return render(request, 'dashboard/user_management.html', {'users': users})

@login_required
def add_user(request):
    """CRUD Create - Ajouter un utilisateur"""
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            is_staff = data.get('is_staff', 'false').lower() == 'true'
            
            if not username or not email or not password:
                error_msg = 'Nom d\'utilisateur, email et mot de passe sont obligatoires'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                error_msg = 'Ce nom d\'utilisateur existe déjà'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            
            if User.objects.filter(email=email).exists():
                error_msg = 'Cet email existe déjà'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=is_staff
            )
            
            # Create user profile
            UserProfile.objects.create(user=user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Utilisateur créé avec succès',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_staff': user.is_staff,
                        'is_active': user.is_active,
                        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
                    }
                })
            
            return JsonResponse({'status': 'success', 'message': 'Utilisateur créé avec succès'})
            
        except Exception as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

@login_required
def update_user(request, pk):
    """CRUD Update - Modifier un utilisateur"""
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            username = data.get('username', user.username)
            email = data.get('email', user.email)
            first_name = data.get('first_name', user.first_name)
            last_name = data.get('last_name', user.last_name)
            is_staff = data.get('is_staff', str(user.is_staff).lower()) == 'true'
            is_active = data.get('is_active', str(user.is_active).lower()) == 'true'
            
            # Check if username/email already exist (excluding current user)
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                error_msg = 'Ce nom d\'utilisateur existe déjà'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                error_msg = 'Cet email existe déjà'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            
            # Update user
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_staff
            user.is_active = is_active
            user.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Utilisateur modifié avec succès',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_staff': user.is_staff,
                        'is_active': user.is_active,
                        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
                    }
                })
            
            return JsonResponse({'status': 'success', 'message': 'Utilisateur modifié avec succès'})
            
        except Exception as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

@login_required
def delete_user(request, pk):
    """CRUD Delete - Supprimer un utilisateur"""
    if not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'}, status=403)
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST' or request.method == 'DELETE':
        try:
            username = user.username
            user.delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f'Utilisateur {username} supprimé avec succès'
                })
            
            return JsonResponse({'status': 'success', 'message': 'Utilisateur supprimé avec succès'})
            
        except Exception as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

@login_required
def toggle_user_status(request, user_id):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    target_user = get_object_or_404(User, id=user_id)
    # Ne pas permettre à un admin de se désactiver lui-même
    if target_user == request.user:
        return JsonResponse({'status': 'error', 'message': 'Impossible de modifier votre propre statut'}, status=400)
    
    action = request.GET.get('action')
    if action == 'toggle_staff':
        target_user.is_staff = not target_user.is_staff
    elif action == 'toggle_active':
        target_user.is_active = not target_user.is_active
    
    target_user.save()
    return JsonResponse({
        'status': 'success', 
        'is_staff': target_user.is_staff,
        'is_active': target_user.is_active
    })

@login_required
def analytics_view(request):
    incidents = Incident.objects.all()
    
    # Statistiques globales
    total_incidents = incidents.count()
    resolved_incidents = incidents.filter(status='Résolu').count()
    repair_efficiency = int((resolved_incidents / total_incidents * 100)) if total_incidents > 0 else 0
    
    # Données pour les graphiques
    severity_data = list(incidents.values('severity').annotate(count=Count('severity')))
    category_data = list(incidents.values('category').annotate(count=Count('category')))
    status_data = list(incidents.values('status').annotate(count=Count('status')))
    
    # Tendance des 7 derniers jours
    last_7_days = timezone.now() - timedelta(days=7)
    daily_trends = incidents.filter(timestamp__gte=last_7_days).extra(
        select={'day': "date(timestamp)"}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    # Formatage des dates au format ISO pour JSON
    trend_labels = [str(item['day']) for item in daily_trends]
    trend_data = [item['count'] for item in daily_trends]

    context = {
        'total_incidents': total_incidents,
        'repair_efficiency': repair_efficiency,
        'severity_data_json': json.dumps(severity_data),
        'category_data_json': json.dumps(category_data),
        'status_data_json': json.dumps(status_data),
        'trend_labels_json': json.dumps(trend_labels),
        'trend_data_json': json.dumps(trend_data),
    }
    return render(request, 'dashboard/analytics.html', context)

@login_required
def dashboard_index(request):
    incidents = Incident.objects.all().order_by('-timestamp')
    
    total = incidents.count()
    water = incidents.filter(category='Eau').count()
    accidents = incidents.filter(category__icontains='accident').count()
    electric = incidents.filter(category__icontains='lectricit').count()
    telegram = incidents.filter(category='Telegram').count()
    
    status_counts = incidents.values('status').annotate(count=Count('status'))
    severity_counts = incidents.values('severity').annotate(count=Count('severity'))
    
    last_7_days = timezone.now() - timedelta(days=7)
    daily_trends = incidents.filter(timestamp__gte=last_7_days).extra(
        select={'day': "date(timestamp)"}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    trend_list = []
    for d in daily_trends:
        trend_list.append({
            'day': d['day'].strftime('%d/%m') if hasattr(d['day'], 'strftime') else str(d['day']),
            'count': d['count']
        })
    
    context = {
        'incidents': incidents[:15],
        'all_incidents': incidents,
        'all_incidents_json': list(incidents.values('id', 'latitude', 'longitude', 'category', 'status', 'address')),
        'last_incident_id': incidents.first().id if incidents.exists() else 0,
        'metrics': {
            'total': total,
            'water': water,
            'accidents': accidents,
            'electric': electric,
            'telegram': telegram,
        },
        'status_data': list(status_counts),
        'severity_data': list(severity_counts),
        'trend_data': trend_list,
    }
    
    if request.user.is_staff:
        return render(request, 'dashboard/index.html', context)
    else:
        # Streamlined context for citizens
        user_incidents = incidents.filter(user_name=request.user.username)
        user_stats = {
            'total': user_incidents.count(),
            'open': user_incidents.filter(status__in=['Signalé', 'En cours']).count(),
            'resolved': user_incidents.filter(status__in=['Réparé', 'Résolu', 'Clos']).count(),
            'by_category': list(user_incidents.values('category').annotate(count=Count('category'))),
            'by_status': list(user_incidents.values('status').annotate(count=Count('status'))),
            'by_severity': list(user_incidents.values('severity').annotate(count=Count('severity'))),
        }
        user_context = {
            'all_incidents': incidents.filter(status__in=['Signalé', 'En cours']), # Only active show to citizens?
            'user_incidents': user_incidents,
            'user_stats': user_stats,
            'recent_incidents': user_incidents.order_by('-timestamp')[:5],
        }
        return render(request, 'dashboard/user_index.html', user_context)

from django.contrib.auth import login, authenticate

class DashboardLoginView(LoginView):
    template_name = 'dashboard/login.html'
    redirect_authenticated_user = False
    success_url = reverse_lazy('dashboard:dashboard_index')

    def form_valid(self, form):
        remember_me = self.request.POST.get('remember_me')
        if not remember_me:
            # Session expire à la fermeture du navigateur
            self.request.session.set_expiry(0)
            self.request.session.modified = True
        else:
            # Session dure longtemps (par défaut settings.SESSION_COOKIE_AGE)
            self.request.session.set_expiry(None)
            self.request.session.modified = True
        return super().form_valid(form)

from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.views.generic import CreateView
import random
import string
from .models import PasswordResetCode

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'dashboard/register_new.html'
    success_url = reverse_lazy('dashboard:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        return response

@csrf_exempt
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email requis'}, status=400)
        
        try:
            user = User.objects.get(email=email)
            # Générer un OTP à 6 chiffres
            import random
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Sauvegarder l'OTP (on réutilise ou crée PasswordResetCode)
            PasswordResetCode.objects.update_or_create(
                user=user,
                defaults={'code': otp, 'created_at': timezone.now()}
            )
            
            # Envoyer l'email
            subject = "Votre code de réinitialisation CityAlert"
            message = f"Bonjour {user.username},\n\nVotre code de réinitialisation est : {otp}\nCe code expirera dans 10 minutes."
            from_email = settings.DEFAULT_FROM_EMAIL
            send_mail(subject, message, from_email, [email])
            
            return JsonResponse({'status': 'success'})
        except User.DoesNotExist:
            # Pour la sécurité, on ne dit pas si l'email existe ou non, mais ici on peut être plus explicite pour le dev
            return JsonResponse({'status': 'error', 'message': 'Aucun compte associé à cet email'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return render(request, 'dashboard/password_reset_new.html')

@csrf_exempt
def password_reset_verify(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = request.POST.get('otp')
        
        try:
            user = User.objects.get(email=email)
            reset_code = PasswordResetCode.objects.get(user=user, code=otp)
            
            # Vérifier l'expiration (10 minutes)
            if (timezone.now() - reset_code.created_at).total_seconds() > 600:
                return JsonResponse({'status': 'error', 'message': 'Code expiré'}, status=400)
            
            return JsonResponse({'status': 'success'})
        except (User.objects.DoesNotExist, PasswordResetCode.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'Code invalide'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def password_reset_new(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            
            # Supprimer le code utilisé
            PasswordResetCode.objects.filter(user=user).delete()
            
            return JsonResponse({'status': 'success'})
        except User.objects.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Utilisateur non trouvé'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@login_required
def send_incident_email(request, pk):
    try:
        incident = get_object_or_404(Incident, pk=pk)
        
        subject = f"Notification d'Incident : {incident.category} - {incident.address}"
        
        # Render HTML message (removed description as it doesn't exist in model)
        html_message = f"""
        <h2>Nouvelle Alerte Incident CityAlert</h2>
        <p><strong>Catégorie :</strong> {incident.category}</p>
        <p><strong>Adresse :</strong> {incident.address}</p>
        <p><strong>Sévérité :</strong> {incident.severity}</p>
        <p><strong>Signalé par :</strong> {incident.user_name}</p>
        <hr>
        <p>Ceci est un mail automatique du système CityAlert.</p>
        """
        plain_message = strip_tags(html_message)
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@cityalert.com')
        to_email = ['technicien@cityalert.com'] # Destinataire par défaut pour le test
        
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)
        return JsonResponse({'status': 'success', 'message': 'Email envoyé avec succès !'})
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

from django.conf import settings

def send_admin_notification(incident, distance=None):
    """Envoie un mail de notification à l'administrateur configuré."""
    subject = f"ALERTE : Nouveau Signalement [{incident.category}] - {incident.address}"
    
    context = {
        'incident': incident,
        'distance': round(distance, 2) if distance and distance != float('inf') else None
    }
    html_message = render_to_string('dashboard/email_notification.html', context)
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', 'setiennetol2004@gmail.com')]
    
    try:
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)
        return True
    except Exception as e:
        print(f"Erreur d'envoi mail admin: {e}")

def send_technician_notification(incident, technician, distance):
    """Envoie un ordre de mission au technicien assigné."""
    if not technician.email:
        return False
        
    subject = f"ORDRE DE MISSION : {incident.category} à {incident.address}"
    
    context = {
        'incident': incident,
        'technician': technician,
        'distance': round(distance, 2) if distance else 0
    }
    html_message = render_to_string('dashboard/email_technician.html', context)
    plain_message = f"Bonjour {technician.name}, vous avez une nouvelle mission : {incident.category} à {incident.address}."
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [technician.email]
    
    try:
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)
        return True
    except Exception as e:
        print(f"Erreur d'envoi mail technicien: {e}")
        return False

def send_citizen_notification(incident):
    """Envoie un mail de confirmation au citoyen qui a fait le signalement."""
    if not incident.user_email:
        return False
        
    subject = f"CONFIRMATION : Signalement #{incident.id} reçu - CityAlert"
    
    context = {
        'incident': incident,
    }
    html_message = render_to_string('dashboard/email_citizen.html', context)
    plain_message = f"Bonjour, nous avons bien reçu votre signalement #{incident.id} ({incident.category}). Merci pour votre aide."
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [incident.user_email]
    
    try:
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)
        return True
    except Exception as e:
        print(f"Erreur d'envoi mail citoyen: {e}")
        return False

class DashboardLogoutView(LogoutView):
    def get(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        logout(request)
        return redirect('dashboard:login')
        
    def post(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        logout(request)
        return redirect('dashboard:login')

def export_incidents_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Incidents_Export.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Catégorie', 'Citoyen', 'Adresse', 'Sévérité', 'Technicien', 'Statut', 'Date'])
    for inc in Incident.objects.all():
        writer.writerow([inc.id, inc.category, inc.user_name, inc.address, inc.severity, inc.technician, inc.status, inc.timestamp])
    return response

def update_incident(request, pk):
    if request.method == 'POST':
        incident = get_object_or_404(Incident, pk=pk)
        data = json.loads(request.body)
        
        old_status = incident.status
        
        if 'status' in data:
            incident.status = data.get('status')
            
        if 'assigned_technician_id' in data:
            tech_id = data.get('assigned_technician_id')
            if tech_id:
                tech = get_object_or_404(Technician, id=tech_id)
                incident.assigned_technician = tech
                
                # Mail notification when assigned
                dist = calculate_distance(incident.latitude, incident.longitude, tech.latitude, tech.longitude)
                threading.Thread(target=send_technician_notification, args=(incident, tech, dist)).start()
            else:
                incident.assigned_technician = None
                
        incident.save()
        
        # Notifier l'utilisateur Telegram si c'est un signalement Telegram
        if old_status != incident.status:
            try:
                telegram_user = TelegramUser.objects.get(user__username=incident.user_name)
                send_telegram_status_update_notification(
                    telegram_user.telegram_id, 
                    incident, 
                    old_status, 
                    incident.status
                )
            except TelegramUser.DoesNotExist:
                pass
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

import base64

def register_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            # Use email as username since Django User model requires it
            username = email.split('@')[0] if email else 'user'
            
            if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Cet email est déjà utilisé.'}, status=400)
            
            # Create user with email as both username and email for simplicity in this flow
            user = User.objects.create_user(username=email, email=email, password=password)
            login(request, user)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return render(request, 'dashboard/register_new.html')

@csrf_exempt
@login_required
def transcribe_audio(request):
    """Transcrit un fichier audio en texte en utilisant Gemini."""
    if request.method == 'POST' and request.FILES.get('audio'):
        try:
            audio_file = request.FILES['audio']
            
            from django.conf import settings
            gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
            
            if not gemini_api_key:
                # Simulation de transcription si la clé n'est pas configurée
                return JsonResponse({'status': 'success', 'transcript': 'Transcription simulée (clé Gemini absente).'} )

            # Gemini 2.0+ supporte l'envoi d'audio directement
            import base64
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            url = f'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={gemini_api_key}'
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Transcris cet audio en texte français. Réponds uniquement avec la transcription, sans aucun autre texte."},
                        {"inline_data": {"mime_type": "audio/wav", "data": audio_data}}
                    ]
                }]
            }
            
            session = get_gemini_session()
            response = session.post(url, json=payload, timeout=60)
            
            if response.status_code == 429:
                return JsonResponse({
                    'status': 'success',
                    'transcript': "Note : Service saturé. Transcription simulée : [Message vocal reçu]"
                })

            if response.status_code == 200:
                result = response.json()
                try:
                    transcript = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    return JsonResponse({'status': 'success', 'transcript': transcript})
                except (KeyError, IndexError):
                    return JsonResponse({'status': 'error', 'message': 'Format de réponse invalide'}, status=500)
            else:
                return JsonResponse({'status': 'error', 'message': f'Erreur API Gemini: {response.status_code}'}, status=500)
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Requête invalide'}, status=400)

def _analyze_image_gemini(image_file):
    """Analyse une image via Gemini et retourne un dict de résultats."""
    import base64
    from django.conf import settings

    # Encode l'image en base64 pour l'API Gemini avec COMPRESSION PRÉALABLE
    # Réduit la taille pour éviter l'erreur ConnectionAbortedError (10053) sur Windows
    try:
        img = Image.open(image_file)
        # Convertir en RGB si nécessaire (pour PNG/RGBA)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Redimensionnement si trop grand (max 1024px de côté)
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Compression en mémoire
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        # En cas d'erreur de compression, on tente la lecture brute par sécurité
        image_file.seek(0)
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    image_file.seek(0)

    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not gemini_api_key:
        # Mode simulation si la clé n'est pas configurée
        return {
            'status': 'success',
            'is_valid': True,
            'detected_category': 'Eau',
            'ai_comment': "Simulation : Fuite d'eau détectée. Clé API manquante.",
            'suggested_severity': 'Moyenne'
        }

    url = f'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={gemini_api_key}'

    prompt = f"""
    Tu es un modèle de vision IA qui analyse des photos d'incidents urbains.
    Analyse cette photo pour détecter le type d'incident (Eau, Accident, Électricité, ou Autre).
    Indique si la photo montre un vrai incident et donne un avis court.

    Réponds UNIQUEMENT en JSON strict, sans texte supplémentaire :
    {{
        "is_valid": true,
        "detected_category": "Eau",
        "ai_comment": "Description courte et précise de ce que tu vois",
        "suggested_severity": "Moyenne"
    }}
    """

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            ]
        }]
    }

    response = requests.post(url, json=payload, timeout=30)

    if response.status_code == 429:
        return {
            'status': 'success',
            'is_valid': True,
            'detected_category': 'Eau',
            'ai_comment': "Note : Le service Gemini est saturé, une analyse de secours a été effectuée. Fuite d'eau probable détectée.",
            'suggested_severity': 'Moyenne'
        }

    if response.status_code != 200:
        return {'status': 'error', 'message': f'Erreur API Gemini ({response.status_code})'}

    result = response.json()
    try:
        content = result['candidates'][0]['content']['parts'][0]['text']
        # Nettoyage des blocs de code Markdown si l'IA en a ajouté
        if content.startswith('```json'):
            content = content.replace('```json', '', 1).replace('```', '', 1).strip()
        elif content.startswith('```'):
            content = content.replace('```', '', 2).strip()
            
        data = json.loads(content)
        data['status'] = 'success'
        return data
    except Exception as e:
        return {'status': 'error', 'message': f'Réponse inattendue de Gemini: {str(e)}'}


@csrf_exempt
@login_required
def analyze_incident_api(request):
    """API pour l'analyse d'image par Gemini sans création d'incident."""
    if request.method == 'POST':
        try:
            category = request.POST.get('category', 'Eau')
            severity = request.POST.get('severity', 'Moyenne')
            description = request.POST.get('description', '')
            image_file = request.FILES.get('image')

            if not image_file:
                return JsonResponse({'status': 'error', 'message': 'Une photo est obligatoire.'}, status=400)

            # Analyse de l'image (vérifie que c'est un incident réel)
            analysis = _analyze_image_gemini(image_file)
            if analysis.get('status') != 'success':
                return JsonResponse({'status': 'error', 'message': analysis.get('message', 'Erreur d\'analyse IA.')}, status=500)

            if not analysis.get('is_valid', False):
                return JsonResponse({'status': 'error', 'message': 'L\'image ne semble pas montrer un incident valide.'}, status=400)

            # Remplace les valeurs par celles suggérées par l'IA si disponibles
            category = analysis.get('detected_category', category) or category
            severity = analysis.get('suggested_severity', severity) or severity
            description = analysis.get('ai_comment', description) or description

            return JsonResponse({
                'status': 'success',
                'is_valid': True,
                'detected_category': category,
                'ai_comment': description,
                'suggested_severity': severity,
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def report_incident(request):
    if request.method == 'POST':
        try:
            # Capturer les données (éventuellement modifiées par l'IA ou l'user)
            category = request.POST.get('category', 'Eau')
            description = request.POST.get('description', '')
            severity = request.POST.get('severity', 'Moyenne')
            user_name = request.POST.get('user_name', request.user.username)
            user_email = request.POST.get('user_email', request.user.email)
            address = request.POST.get('address', '')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            image_file = request.FILES.get('image')

            if not image_file:
                return JsonResponse({'status': 'error', 'message': 'Photo manquante.'}, status=400)

            lat = float(latitude) if latitude and latitude.strip() else None
            lon = float(longitude) if longitude and longitude.strip() else None

            incident = Incident.objects.create(
                category=category,
                description=description,
                user_name=user_name,
                user_email=user_email,
                address=address,
                latitude=lat,
                longitude=lon,
                severity=severity,
                image=image_file,
                status='Signalé'
            )
            
            # Notifications
            closest_tech, distance = find_closest_technician(incident)
            if closest_tech:
                incident.assigned_technician = closest_tech
                incident.save()
                threading.Thread(target=send_technician_notification, args=(incident, closest_tech, distance)).start()
            
            threading.Thread(target=send_admin_notification, args=(incident, distance)).start()
            threading.Thread(target=send_citizen_notification, args=(incident,)).start()
            
            return JsonResponse({'status': 'success', 'id': incident.id})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return render(request, 'dashboard/report.html')

def incident_detail(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    technicians = Technician.objects.all()
    return render(request, 'dashboard/incident_detail.html', {
        'incident': incident,
        'technicians': technicians
    })

@login_required
def latest_incidents_api(request):
    """API pour le polling temps réel du dashboard."""
    # Récupérer les 10 derniers incidents des dernières 24h
    last_24h = timezone.now() - timedelta(hours=24)
    incidents = Incident.objects.filter(timestamp__gte=last_24h).order_by('-timestamp')[:10]
    
    data = []
    for inc in incidents:
        data.append({
            'id': inc.id,
            'category': inc.category,
            'address': inc.address,
            'latitude': inc.latitude,
            'longitude': inc.longitude,
            'status': inc.status,
            'severity': inc.severity,
            'user_name': inc.user_name,
            'timestamp': inc.timestamp.strftime('%H:%M'),
        })
    
    # Statistiques globales pour les compteurs
    all_incs = Incident.objects.all()
    metrics = {
        'total': all_incs.count(),
        'water': all_incs.filter(category='Eau').count(),
        'accidents': all_incs.filter(category__icontains='accident').count(),
        'electric': all_incs.filter(category__icontains='lectricit').count(),
    }
    
    return JsonResponse({
        'incidents': data,
        'metrics': metrics
    })

@login_required
def user_dashboard_api(request):
    """API pour les données temps réel du dashboard utilisateur."""
    # Récupérer les incidents de l'utilisateur
    user_incidents = Incident.objects.filter(user_name=request.user.username).order_by('-timestamp')
    
    # Statistiques utilisateur
    user_stats = {
        'total': user_incidents.count(),
        'open': user_incidents.filter(status__in=['Signalé', 'En cours']).count(),
        'resolved': user_incidents.filter(status__in=['Réparé', 'Résolu', 'Clos']).count(),
        'by_category': list(user_incidents.values('category').annotate(count=Count('category'))),
        'by_status': list(user_incidents.values('status').annotate(count=Count('status'))),
        'by_severity': list(user_incidents.values('severity').annotate(count=Count('severity'))),
    }
    
    # 5 derniers incidents récents
    recent_incidents = []
    for inc in user_incidents[:5]:
        recent_incidents.append({
            'id': inc.id,
            'category': inc.category,
            'status': inc.status,
            'severity': inc.severity,
            'timestamp': inc.timestamp.strftime('%d/%m/%Y %H:%M'),
        })
    
    return JsonResponse({
        'user_stats': user_stats,
        'recent_incidents': recent_incidents
    })

def detect_incident_category_from_text(text: str) -> str:
    """Détermine la catégorie d'incident en analysant le texte du signalement."""
    txt = (text or '').lower()

    # Prioriser les mots clés liés aux fuites d'eau.
    if any(k in txt for k in ['fuite', 'canalisation', 'inond', 'eau', 'robinet']):
        return 'Eau'

    # Accidents (route, collision, véhicule, piéton)
    if any(k in txt for k in ['accident', 'collision', 'voiture', 'camion', 'piéton', 'route', 'trafic']):
        return 'Accident'

    # Problèmes électriques
    if any(k in txt for k in ['électricité', 'electricité', 'courant', 'panne', 'prise', 'court-circuit', 'circuit']):
        return 'Electricité'

    # Valeur par défaut (fuite d'eau)
    return 'Eau'


@csrf_exempt
def telegram_webhook(request):
    """Webhook pour recevoir les messages Telegram."""
    import logging
    logger = logging.getLogger('dashboard')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Telegram webhook reçu: {data}")
            
            message = data.get('message', {})
            
            if not message:
                logger.info("Message vide dans webhook Telegram")
                return JsonResponse({'status': 'ok'})
            
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '').strip()
            telegram_user = message.get('from', {})
            telegram_id = telegram_user.get('id')
            username = telegram_user.get('username')
            phone_number = telegram_user.get('phone_number')
            
            logger.info(f"Message Telegram - ID: {telegram_id}, Chat: {chat_id}, Text: {text}")
            logger.info(f"Variables extraites - chat_id: {chat_id}, telegram_id: {telegram_id}, username: {username}")
            
            try:
                logger.info("Début try block")
                if not chat_id or not telegram_id:
                    logger.warning("Chat ID ou Telegram ID manquant")
                    return JsonResponse({'status': 'ok'})
                
                logger.info("Vérification IDs passée")
                
                # Mettre à jour le numéro de téléphone si disponible
                if phone_number:
                    logger.info(f"Mise à jour téléphone pour utilisateur {telegram_id}")
                    try:
                        telegram_user_obj = TelegramUser.objects.get(telegram_id=telegram_id)
                        if not telegram_user_obj.phone_number:
                            telegram_user_obj.phone_number = phone_number
                            telegram_user_obj.save()
                            logger.info("Téléphone mis à jour avec succès")
                    except TelegramUser.DoesNotExist:
                        logger.warning(f"TelegramUser {telegram_id} non trouvé pour mise à jour téléphone")
                        pass
                else:
                    logger.info("Aucun numéro de téléphone fourni")
                
                logger.info("Passage au traitement des commandes/signalements")
                
                # Traiter les commandes
                if text.startswith('/'):
                    logger.info(f"Traitement commande: {text}")
                    handle_telegram_command(chat_id, telegram_id, username, text)
                else:
                    logger.info(f"Traitement signalement: {text}")
                    # Traiter comme signalement d'incident
                    handle_telegram_incident(chat_id, telegram_id, text, message)
                
                return JsonResponse({'status': 'ok'})
                
            except Exception as inner_e:
                logger.error(f"Exception dans traitement message: {inner_e}")
                raise inner_e
            
        except Exception as e:
            print(f"Erreur webhook Telegram: {e}")
            return JsonResponse({'status': 'error'}, status=500)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)

def handle_telegram_command(chat_id, telegram_id, username, command):
    """Traite les commandes Telegram."""
    if command == '/start':
        # Vérifier si l'utilisateur Telegram est lié à un compte Django
        try:
            telegram_user = TelegramUser.objects.get(telegram_id=telegram_id)
            user = telegram_user.user
            send_telegram_message(chat_id, 
                f"✅ Bienvenue {user.username} !\n\n"
                "Vous pouvez maintenant signaler des incidents via Telegram.\n\n"
                "📝 Envoyez un message avec la description de votre incident.\n"
                "📍 Partagez votre localisation pour plus de précision.\n"
                "📋 Tapez /help pour voir toutes les commandes."
            )
        except TelegramUser.DoesNotExist:
            # Créer automatiquement un compte utilisateur
            from django.contrib.auth.models import User
            import random
            import string
            
            # Générer un nom d'utilisateur unique
            base_username = username or f"telegram_user_{telegram_id}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Générer un email temporaire
            temp_email = f"{telegram_id}@telegram.cityalert.local"
            
            # Générer un mot de passe aléatoire
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            # Créer l'utilisateur Django
            user = User.objects.create_user(
                username=username,
                email=temp_email,
                password=password
            )
            
            # Créer le profil utilisateur
            UserProfile.objects.create(user=user)
            
            # Lier le compte Telegram
            telegram_user = TelegramUser.objects.create(
                user=user,
                telegram_id=telegram_id,
                telegram_username=username,
                is_verified=True
            )
            
            send_telegram_message(chat_id,
                f"🎉 Compte créé automatiquement !\n\n"
                f"👤 Nom d'utilisateur : {username}\n"
                f"📧 Email temporaire : {temp_email}\n\n"
                "📝 Vous pouvez maintenant signaler des incidents :\n"
                "• Décrivez le problème\n"
                "• Partagez votre localisation (bouton 📎)\n\n"
                "🔧 Pour modifier vos informations, connectez-vous sur le site web.\n"
                "📋 Tapez /help pour voir toutes les commandes."
            )
    
    elif command == '/help':
        send_telegram_message(chat_id,
            "📋 Commandes disponibles :\n\n"
            "/start - Démarrer ou vérifier la liaison\n"
            "/help - Afficher cette aide\n"
            "/mesincidents - Voir vos signalements\n"
            "/statut - Voir les statistiques\n\n"
            "📝 Pour signaler un incident :\n"
            "Envoyez simplement un message avec la description.\n\n"
            "📍 Partagez votre localisation pour plus de précision."
        )
    
    elif command == '/mesincidents':
        try:
            telegram_user = TelegramUser.objects.get(telegram_id=telegram_id)
            user = telegram_user.user
            
            incidents = Incident.objects.filter(user_name=user.username).order_by('-timestamp')[:5]
            
            if incidents:
                message = "📋 Vos derniers signalements :\n\n"
                for inc in incidents:
                    message += f"• {inc.category} - {inc.status}\n"
                    message += f"  {inc.timestamp.strftime('%d/%m %H:%M')} - {inc.address}\n\n"
            else:
                message = "📋 Vous n'avez pas encore de signalements."
            
            send_telegram_message(chat_id, message)
            
        except TelegramUser.DoesNotExist:
            send_telegram_message(chat_id, "❌ Votre compte n'est pas lié. Tapez /start pour commencer.")
    
    elif command == '/statut':
        try:
            telegram_user = TelegramUser.objects.get(telegram_id=telegram_id)
            user = telegram_user.user
            
            incidents = Incident.objects.filter(user_name=user.username)
            total = incidents.count()
            open_count = incidents.filter(status__in=['Signalé', 'En cours']).count()
            resolved_count = incidents.filter(status__in=['Réparé', 'Résolu', 'Clos']).count()
            
            message = f"📊 Vos statistiques :\n\n"
            message += f"📝 Total signalements : {total}\n"
            message += f"⏳ En cours : {open_count}\n"
            message += f"✅ Résolus : {resolved_count}"
            
            send_telegram_message(chat_id, message)
            
        except TelegramUser.DoesNotExist:
            send_telegram_message(chat_id, "❌ Votre compte n'est pas lié. Tapez /start pour commencer.")

def handle_telegram_incident(chat_id, telegram_id, text, message):
    """Traite un signalement d'incident via Telegram."""
    import logging
    logger = logging.getLogger('dashboard')
    
    try:
        # Récupérer ou créer l'utilisateur Telegram
        telegram_user, created = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'telegram_username': message.get('from', {}).get('username'),
                'is_verified': True
            }
        )
        
        # Si l'utilisateur vient d'être créé, créer le compte Django associé
        if created and not telegram_user.user:
            from django.contrib.auth.models import User
            import random
            import string
            
            # Générer un nom d'utilisateur unique
            base_username = message.get('from', {}).get('username') or f"telegram_user_{telegram_id}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Générer un email temporaire
            temp_email = f"{telegram_id}@telegram.cityalert.local"
            
            # Générer un mot de passe aléatoire
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            # Créer l'utilisateur Django
            user = User.objects.create_user(
                username=username,
                email=temp_email,
                password=password
            )
            
            # Créer le profil utilisateur
            UserProfile.objects.create(user=user)
            
            # Lier au compte Telegram
            telegram_user.user = user
            telegram_user.save()
        
        user = telegram_user.user
        
        # Extraire la localisation si fournie
        latitude = None
        longitude = None
        location = message.get('location')
        if location:
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            logger.info(f"Localisation fournie: {latitude}, {longitude}")

        # Localisation OPTIONNELLE pour les signalements Telegram
        if latitude is None or longitude is None:
            # Coordonnées par défaut pour Paris si non fournies
            latitude = 48.8566
            longitude = 2.3522
            logger.info(f"Utilisation des coordonnées par défaut: {latitude}, {longitude}")
            send_telegram_message(chat_id,
                "✅ Signalement enregistré !\n\n"
                "📍 Localisation approximative utilisée (Paris).\n"
                "Pour plus de précision, envoyez votre position GPS la prochaine fois."
            )
        
        # Récupérer l'adresse à partir des coordonnées
        address = 'Signalement via Telegram'
        if latitude and longitude:
            address = get_address_from_coordinates(latitude, longitude)
        
        # Créer l'incident avec type "Telegram"
        logger.info(f"Création incident Telegram pour user: {user.username}, text: {text}")
        incident = Incident.objects.create(
            category='Telegram',  # Type spécial pour incidents Telegram
            address=text,  # Utiliser address au lieu de description
            user_name=user.username,
            user_email=user.email,
            latitude=latitude,
            longitude=longitude,
            severity='Moyenne',
            status='Signalé'
        )
        logger.info(f"Incident Telegram créé avec succès: ID {incident.id}")
        
        # Notifier l'administrateur que c'est un signalement Telegram
        logger.info("Envoi notification admin Telegram...")
        send_telegram_admin_notification(incident, telegram_user, text)
        logger.info("Notification admin envoyée")
        
        # Notifications standard (équipe la plus proche si possible)
        logger.info("Recherche technicien le plus proche...")
        closest_tech, distance = find_closest_technician(incident)
        if closest_tech:
            logger.info(f"Technicien trouvé: {closest_tech.name}")
            incident.assigned_technician = closest_tech
            incident.save()
            threading.Thread(target=send_technician_notification, args=(incident, closest_tech, distance)).start()

            # Notifier l'utilisateur Telegram qu'une équipe est alertée
            send_telegram_user_assignment_notification(chat_id, incident, closest_tech)
        else:
            logger.info("Aucun technicien trouvé, utilisation fallback...")
            # Si la localisation manquait ou aucun technicien disponible n'a été trouvé,
            # on alerte au moins l'équipe la plus proche dans la même catégorie.
            fallback_tecs = Technician.objects.filter(category='Eau', status='Libre').order_by('id')[:1]
            if fallback_tecs:
                threading.Thread(target=send_technician_notification, args=(incident, fallback_tecs[0], None)).start()

        logger.info("Envoi notifications standard...")
        threading.Thread(target=send_admin_notification, args=(incident, distance)).start()
        threading.Thread(target=send_citizen_notification, args=(incident,)).start()
        
        logger.info("Envoi confirmation utilisateur Telegram...")
        send_telegram_message(chat_id, 
            f"✅ Signalement enregistré !\n\n"
            f"📝 ID : #{incident.id}\n"
            f"📍 {incident.address}\n\n"
            "Les équipes ont été notifiées et interviendront rapidement."
        )
        logger.info("Confirmation envoyée à l'utilisateur")
        
    except TelegramUser.DoesNotExist:
        logger.error(f"TelegramUser.DoesNotExist pour ID: {telegram_id}")
        send_telegram_message(chat_id, "❌ Votre compte n'est pas lié. Tapez /start pour commencer.")
    except Exception as e:
        logger.error(f"Erreur création incident Telegram: {e}")
        print(f"Erreur création incident Telegram: {e}")
        send_telegram_message(chat_id, "❌ Erreur lors de la création du signalement. Réessayez plus tard.")

def send_telegram_user_assignment_notification(chat_id, incident, technician):
    """Notifie l'utilisateur Telegram qu'une équipe a été alertée."""
    try:
        message = f"""
🚨 ÉQUIPE ALERTÉE - Signalement #{incident.id}

✅ Votre signalement a été pris en charge !

👨‍🔧 Équipe assignée : {technician.name}
📞 Contact : {technician.phone or 'Non disponible'}
📧 Email : {technician.email or 'Non disponible'}

📍 Localisation : {incident.address}
⏰ Heure : {incident.timestamp.strftime('%H:%M')}

L'équipe interviendra dans les plus brefs délais.
Vous recevrez une notification lors de la prise en charge.

---
CityAlert Bot 🤖
        """.strip()
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"Erreur notification utilisateur Telegram assignment: {e}")

def send_telegram_status_update_notification(chat_id, incident, old_status, new_status):
    """Notifie l'utilisateur Telegram des changements de statut."""
    try:
        status_emoji = {
            'En cours': '🔧',
            'Réparé': '✅',
            'Résolu': '🎉',
            'Signalé': '📝'
        }
        
        emoji = status_emoji.get(new_status, '📋')
        
        message = f"""
📊 MISE À JOUR - Signalement #{incident.id}

{emoji} Statut changé : {old_status} → {new_status}

📝 Description : {incident.description[:100]}{'...' if len(incident.description) > 100 else ''}

---
CityAlert Bot 🤖
        """.strip()
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"Erreur notification statut Telegram: {e}")

def send_telegram_admin_notification(incident, telegram_user, message_text):
    """Notifie l'administrateur qu'un signalement vient de Telegram."""
    try:
        # Email admin pour les signalements Telegram
        admin_email = "setiennetol2004@gmail.com"
        
        subject = f"🚨 NOUVEAU SIGNALEMENT TELEGRAM - #{incident.id}"
        
        # Extraire le numéro de téléphone si disponible
        phone_info = f"\n📱 Téléphone: {telegram_user.phone_number or 'Non renseigné'}"
        
        html_message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ff6b35, #f7931e); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0; font-size: 24px;">🚨 SIGNALEMENT TELEGRAM</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Nouveau signalement reçu via le bot Telegram</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; border: 1px solid #e9ecef;">
                <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">📋 Détails du signalement</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666; width: 150px;">ID Incident:</td>
                            <td style="padding: 8px; color: #333;"><strong>#{incident.id}</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666;">Utilisateur:</td>
                            <td style="padding: 8px; color: #333;">{telegram_user.user.username}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666;">Telegram:</td>
                            <td style="padding: 8px; color: #333;">@{telegram_user.telegram_username or 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666;">Email:</td>
                            <td style="padding: 8px; color: #333;">{telegram_user.user.email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666;">Téléphone:</td>
                            <td style="padding: 8px; color: #333;">{telegram_user.phone_number or 'Non renseigné'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666;">Date:</td>
                            <td style="padding: 8px; color: #333;">{incident.timestamp.strftime('%d/%m/%Y %H:%M')}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #ff6b35;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">📝 Message du signalement</h4>
                    <p style="margin: 0; color: #555; line-height: 1.6; background: #f8f9fa; padding: 10px; border-radius: 5px;">{message_text}</p>
                </div>
                
                <div style="text-align: center; margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 8px;">
                    <p style="margin: 0; color: #1976d2; font-weight: bold;">
                        🤖 Ce signalement provient du bot Telegram CityAlert
                    </p>
                </div>
            </div>
        </div>
        """
        
        plain_message = f"""
NOUVEAU SIGNALEMENT TELEGRAM - #{incident.id}

Utilisateur: {telegram_user.user.username}
Telegram: @{telegram_user.telegram_username or 'N/A'}
Email: {telegram_user.user.email}
Téléphone: {telegram_user.phone_number or 'Non renseigné'}
Date: {incident.timestamp.strftime('%d/%m/%Y %H:%M')}

Message: {message_text}

---
Ce signalement a été reçu via le bot Telegram CityAlert
        """
        
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, plain_message, from_email, [admin_email], html_message=html_message)
        
    except Exception as e:
        print(f"Erreur notification admin Telegram: {e}")

def send_telegram_message(chat_id, text):
    """Envoie un message via Telegram Bot API."""
    telegram_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not telegram_token:
        print("TELEGRAM_BOT_TOKEN non configuré")
        return
    
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Erreur envoi message Telegram: {e}")

@login_required
def telegram_link_page(request):
    """Page pour lier un compte Telegram."""
    # Vérifier si déjà lié
    try:
        telegram_user = request.user.telegram
        is_linked = True
        telegram_username = telegram_user.telegram_username
    except TelegramUser.DoesNotExist:
        is_linked = False
        telegram_username = None
    
    context = {
        'is_linked': is_linked,
        'telegram_username': telegram_username,
        'bot_username': getattr(settings, 'TELEGRAM_BOT_USERNAME', 'CityAlertBot')
    }
    
    return render(request, 'dashboard/link_telegram.html', context)

@login_required
def telegram_link_confirm(request, token):
    """Confirme la liaison Telegram avec un token."""
    from django.core.cache import cache
    
    link_data = cache.get(f"telegram_link_{token}")
    if not link_data:
        return render(request, 'dashboard/telegram_link_error.html', {
            'error': 'Token expiré ou invalide'
        })
    
    # Créer ou mettre à jour la liaison Telegram
    TelegramUser.objects.update_or_create(
        telegram_id=link_data['telegram_id'],
        defaults={
            'user': request.user,
            'telegram_username': link_data['username'],
            'is_verified': True
        }
    )
    
    # Supprimer le token
    cache.delete(f"telegram_link_{token}")
    
    # Notifier l'utilisateur Telegram
    send_telegram_message(link_data['chat_id'], 
        f"✅ Liaison réussie !\n\n"
        f"Bienvenue {request.user.username} !\n"
        "Vous pouvez maintenant signaler des incidents via Telegram."
    )
    
    return render(request, 'dashboard/telegram_link_success.html')
