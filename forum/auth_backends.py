from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from forum.models import UserAccount

class CustomUserAccountBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = UserAccount.objects.get(Email=username)
            if check_password(password, user.Password):
                return user
        except UserAccount.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return UserAccount.objects.get(pk=user_id)
        except UserAccount.DoesNotExist:
            return None
