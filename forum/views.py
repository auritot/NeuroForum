from django.shortcuts import render
from .models import UserAccount

# Create your views here.
def index(request):
    users = UserAccount.objects.all()
    return render(request, 'html/index.html', {'users': users})
