from dashboard.models import Incident, TelegramUser
from django.core.mail import send_mail

# Récupérer le dernier incident Telegram
try:
    last_incident = Incident.objects.filter(category='Telegram').last()
    if last_incident:
        print('Dernier incident Telegram:', last_incident.id)
        
        # Récupérer l'utilisateur Telegram
        telegram_user = TelegramUser.objects.filter(user__username=last_incident.user_name).first()
        if telegram_user:
            print('Utilisateur Telegram trouvé:', telegram_user.telegram_username)
            
            # Créer le message HTML simple
            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #ff6b35, #f7931e); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                    <h2 style="margin: 0; font-size: 24px;">SIGNALEMENT TELEGRAM</h2>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Nouveau signalement reçu via le bot Telegram</p>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; border: 1px solid #e9ecef;">
                    <p><strong>ID Incident:</strong> #{last_incident.id}</p>
                    <p><strong>Utilisateur:</strong> {telegram_user.user.username}</p>
                    <p><strong>Telegram:</strong> @{telegram_user.telegram_username or 'N/A'}</p>
                    <p><strong>Email:</strong> {telegram_user.user.email}</p>
                    <p><strong>Téléphone:</strong> {telegram_user.phone_number or 'Non renseigné'}</p>
                    <p><strong>Date:</strong> {last_incident.timestamp.strftime('%d/%m/%Y %H:%M')}</p>
                </div>
            </div>
            """
            
            # Envoyer l'email directement
            result = send_mail(
                f'NOUVEAU SIGNALEMENT TELEGRAM - #{last_incident.id}',
                f'Signalement Telegram #{last_incident.id} de {telegram_user.user.username}',
                'setiennetol2004@gmail.com',
                ['setiennetol2004@gmail.com'],
                html_message=html_message,
                fail_silently=False,
            )
            print('Email envoyé, résultat:', result)
        else:
            print('Utilisateur Telegram non trouvé')
    else:
        print('Aucun incident Telegram trouvé')
        
except Exception as e:
    print('ERREUR:', str(e))
    import traceback
    traceback.print_exc()
