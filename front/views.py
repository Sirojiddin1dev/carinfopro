from django.shortcuts import render, get_object_or_404
from main.models import User


def index(request):
    return render(request, 'front/index.html')


def user_chat(request, user_id):
    user = get_object_or_404(User, id=user_id, is_active=True)
    if not user.is_profile_public:
        return render(request, 'front/user.html', {
            'user_id': str(user_id),
            'is_public': False
        })
    return render(request, 'front/user.html', {
        'user_id': str(user_id),
        'is_public': True,
        'user': user
    })
