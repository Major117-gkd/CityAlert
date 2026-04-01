from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class EmailBackend(BaseBackend):
    """
    Custom authentication backend that allows users to login with their email address
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try to find users by email first, prioritize admin accounts if duplicates
        users = User.objects.filter(email=username).order_by('-is_superuser', '-is_staff')
        for user in users:
            if user.check_password(password):
                return user
        
        # Fallback to username if no email matched or password was wrong
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
            
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
