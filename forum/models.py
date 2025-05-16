from django.db import models

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

    def __str__(self):
        return f"{self.Timestamp}: {self.LogContent}"

