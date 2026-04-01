from django.db import models
from django.contrib.auth.models import User

class Incident(models.Model):
    CATEGORY_CHOICES = [
        ('Eau', 'Fuite d\'eau'),
        ('Accident', 'Accident de la route'),
        ('Electricité', 'Court-circuit / Panne'),
        ('Telegram', 'Signalement Telegram'),
    ]
    
    STATUS_CHOICES = [
        ('Signalé', 'Signalé'),
        ('En cours', 'En cours'),
        ('Réparé', 'Réparé'),
    ]
    
    SEVERITY_CHOICES = [
        ('Élevée', 'Élevée'),
        ('Moyenne', 'Moyenne'),
        ('Petite', 'Petite'),
        ('Inconnue', 'Inconnue'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Eau')
    user_id = models.BigIntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=255, null=True, blank=True)
    user_email = models.EmailField(null=True, blank=True)
    image = models.ImageField(upload_to='incidents/', null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    severity = models.CharField(max_length=50, choices=SEVERITY_CHOICES, default='Inconnue')
    ai_severity = models.CharField(max_length=50, choices=SEVERITY_CHOICES, default='Inconnue')
    assigned_technician = models.ForeignKey('Technician', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_incidents')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Signalé')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'incidents'
        verbose_name = 'Incident'
        verbose_name_plural = 'Incidents'

    def __str__(self):
        return f"{self.category} #{self.id} - {self.status}"

class Technician(models.Model):
    CATEGORY_CHOICES = [
        ('Eau', 'Fuite d\'eau'),
        ('Accident', 'Accident de la route'),
        ('Electricité', 'Court-circuit / Panne'),
    ]
    
    STATUS_CHOICES = [
        ('Libre', 'Libre'),
        ('En mission', 'En mission'),
    ]
    
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Eau')
    specialty = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Libre')
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True, help_text="Email de l'équipe pour recevoir les alertes")
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude du local ou de la ville de l'équipe")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude du local ou de la ville de l'équipe")
    missions_completed = models.IntegerField(default=0)
    avatar_color = models.CharField(max_length=50, default='var(--accent-orange)')
    
    class Meta:
        db_table = 'technicians'
        verbose_name = 'Technicien'
        verbose_name_plural = 'Techniciens'

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"Profil de {self.user.username}"

class TelegramUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram')
    telegram_id = models.BigIntegerField(unique=True)
    telegram_username = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Telegram: {self.telegram_username or self.telegram_id}"

class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_codes'
