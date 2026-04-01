from .models import UserProfile


def user_profile(request):
    """Expose the authenticated user's profile to all templates.

    This ensures we can safely access `user_profile.avatar` without needing to
    create the profile in every view.
    """
    if not request.user.is_authenticated:
        return {}

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return {'user_profile': profile}
