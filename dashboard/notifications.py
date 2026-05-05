import os
import threading
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_admin_notification(incident, distance=None):
    """Envoie un mail de notification à l'administrateur configuré."""
    subject = f"ALERTE : Nouveau Signalement [{incident.category}] - {incident.address}"
    
    context = {
        'incident': incident,
        'distance': round(distance, 2) if distance and distance != float('inf') else None
    }
    try:
        html_message = render_to_string('dashboard/email_notification.html', context)
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', 'setiennetol2004@gmail.com')]
        
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)
        return True
    except Exception as e:
        print(f"Erreur d'envoi mail admin: {e}")
        return False

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
    try:
        html_message = render_to_string('dashboard/email_technician.html', context)
        plain_message = f"Bonjour {technician.name}, vous avez une nouvelle mission : {incident.category} à {incident.address}."
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [technician.email]
        
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
    try:
        html_message = render_to_string('dashboard/email_citizen.html', context)
        plain_message = f"Bonjour, nous avons bien reçu votre signalement #{incident.id} ({incident.category}). Merci pour votre aide."
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [incident.user_email]
        
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)
        return True
    except Exception as e:
        print(f"Erreur d'envoi mail citoyen: {e}")
        return False

def send_telegram_status_notification(telegram_user_id, incident_id, new_status, bot_token):
    """
    Envoie une notification Telegram quand le statut d'un incident change.
    Utilisé par le dashboard pour notifier l'utilisateur qui a signalé via le bot.
    """
    import asyncio
    from telegram import Bot
    
    status_msg = {
        "En cours": f"🛠️ Votre signalement #{incident_id} est maintenant **en cours d'intervention**.",
        "Réparé": f"✅ Bonne nouvelle ! L'incident signalé (#{incident_id}) a été **réparé**. Merci de votre aide !",
        "Résolu": f"✅ Bonne nouvelle ! L'incident signalé (#{incident_id}) a été **résolu**. Merci de votre aide !"
    }
    msg = status_msg.get(new_status, f"ℹ️ Le statut de votre signalement #{incident_id} a été mis à jour : **{new_status}**.")
    
    async def send():
        try:
            bot = Bot(token=bot_token)
            await bot.send_message(chat_id=telegram_user_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            print(f"Erreur notification Telegram: {e}")

    # Run in a separate thread/loop to not block Django
    threading.Thread(target=lambda: asyncio.run(send())).start()
