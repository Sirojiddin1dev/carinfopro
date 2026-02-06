from django.shortcuts import render


def index(request):
    return render(request, 'front/index.html')


def user_chat(request, user_id):
    return render(request, 'front/user.html', {'user_id': str(user_id)})
