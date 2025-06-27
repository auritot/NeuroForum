from django.db import models
from django.conf import settings
from forum.crypto_utils import encrypt_message, decrypt_message

# Create your models here.
class UserAccount(models.Model):
    UserID = models.AutoField(primary_key=True)
    Username = models.CharField(max_length=255)
    Email = models.CharField(max_length=255)
    Password = models.CharField(max_length=255)
    Role = models.CharField(max_length=50)
    EmailVerificationCode = models.CharField(max_length=255)

    def __str__(self):
        return self.Username
    
    @property
    def is_authenticated(self):
        return True
    
class Post(models.Model):
    PostID = models.AutoField(primary_key=True)
    Title = models.CharField(max_length=255)
    PostContent = models.CharField(max_length=255)
    Timestamp = models.DateTimeField(auto_now_add=True)
    CommentStatus = models.BooleanField(default=True)
    UserID = models.ForeignKey(UserAccount, on_delete=models.CASCADE)

    def __str__(self):
        return self.Title


class Comment(models.Model):
    CommentID = models.AutoField(primary_key=True)
    CommentContents = models.CharField(max_length=255)
    Timestamp = models.DateTimeField(auto_now_add=True)
    UserID = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
    PostID = models.ForeignKey(Post, on_delete=models.CASCADE)

    def __str__(self):
        return f"Comment {self.CommentID} on Post {self.PostID}"


class Filtering(models.Model):
    FilterID = models.AutoField(primary_key=True)
    FilterContent = models.CharField(max_length=255)

    def __str__(self):
        return self.FilterContent


class Logs(models.Model):
    LogID = models.AutoField(primary_key=True)
    Timestamp = models.DateTimeField(auto_now_add=True)
    LogContent = models.CharField(max_length=255)
    Category = models.CharField(max_length=50, default='uncategorized')
    UserID = models.ForeignKey(UserAccount, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.Timestamp}: {self.LogContent}"

class ChatRoom(models.Model):

    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name
    
    @classmethod
    def get_or_create_private(cls, user1: str, user2: str):
        a, b = sorted([user1.lower(), user2.lower()])
        room_name = f"private_{a}_{b}"
        room, _ = cls.objects.get_or_create(name=room_name)
        return room
    
    @classmethod
    def get_recent_partners_for_user(cls, username: str):
        from django.db.models import Q

        username = username.lower()

        all_sessions = ChatSession.objects.filter(
            Q(messages__sender__Username__iexact=username) |
            Q(room__name__icontains=f"_{username}")  # include any private chatroom involving user
        ).select_related("room").distinct()

        partner_usernames = set()

        for session in all_sessions:
            room_name = session.room.name
            if not room_name.startswith("private_"):
                continue
            try:
                a, b = room_name.replace("private_", "").split("_")
            except ValueError:
                continue

            a = a.lower()
            b = b.lower()
            if a == username and b != username:
                partner_usernames.add(b)
            elif b == username and a != username:
                partner_usernames.add(a)

        return sorted(partner_usernames)



class ChatSession(models.Model):
    """
    A ChatSession lives inside exactly one ChatRoom.
    It has a start and end time; any ChatMessage in this session belongs here.
    When one user leaves and the other is still there, the session is still "open".
    When the last participant disconnects, we set ended_at=now() to close the session.
    """
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]  # newest sessions first

    def __str__(self):
        if self.ended_at:
            return (
                f"{self.room.name} ("
                f"{self.started_at.strftime('%H:%M %d/%m/%Y')} → "
                f"{self.ended_at.strftime('%H:%M %d/%m/%Y')}"
                f")"
            )
        return f"{self.room.name} (Open since {self.started_at.strftime('%H:%M %d/%m/%Y')})"

class ChatMessage(models.Model):
    """
    Now each message belongs to a specific ChatSession instead of directly to ChatRoom.
    When you fetch “history,” you’ll pull all messages from sessions where ended_at != None.
    When you’re in an active session, you only pull messages with session.ended_at == None.
    """
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
    content_encrypted = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]  # old → new

    @property
    def content(self):
        try:
            return decrypt_message(self.content_encrypted)
        except Exception:
            return "[Decryption Failed]"

    @content.setter
    def content(self, value):
        self.content_encrypted = encrypt_message(value)

    def __str__(self):
        ts = self.timestamp.strftime("%H:%M %d/%m/%Y")
        return f"[{ts}] {self.sender.username}: {self.content[:40]}…"
    

# class ChatUnread(models.Model):
#     user = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
#     room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
#     unread_count = models.PositiveIntegerField(default=0)

#     class Meta:
#         unique_together = ("user", "room")