from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from forum.models import UserAccount

class CustomUserAccountBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        print(f"[DEBUG] Attempting auth for {username}")

        try:
            user = UserAccount.objects.get(Email=username)
            print(f"[DEBUG] Found user. Hashed password: {user.Password}")

            if check_password(password, user.Password):
                print("[DEBUG] Password matched.")
                return user
            else:
                print("[DEBUG] Password did NOT match.")
        except UserAccount.DoesNotExist:
            print("[DEBUG] User not found.")

        return None

    def get_user(self, user_id):
        try:
            return UserAccount.objects.get(pk=user_id)
        except UserAccount.DoesNotExist:
            return None
