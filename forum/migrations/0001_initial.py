# Generated by Django 5.2.3 on 2025-06-27 11:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChatRoom",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=128, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Filtering",
            fields=[
                ("FilterID", models.AutoField(primary_key=True, serialize=False)),
                ("FilterContent", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="UserAccount",
            fields=[
                ("UserID", models.AutoField(primary_key=True, serialize=False)),
                ("Username", models.CharField(max_length=255)),
                ("Email", models.CharField(max_length=255)),
                ("Password", models.CharField(max_length=255)),
                ("Role", models.CharField(max_length=50)),
                ("EmailVerificationCode", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="ChatSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to="forum.chatroom",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="Post",
            fields=[
                ("PostID", models.AutoField(primary_key=True, serialize=False)),
                ("Title", models.CharField(max_length=255)),
                ("PostContent", models.CharField(max_length=255)),
                ("Timestamp", models.DateTimeField(auto_now_add=True)),
                ("CommentStatus", models.BooleanField(default=True)),
                (
                    "UserID",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="forum.useraccount",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Logs",
            fields=[
                ("LogID", models.AutoField(primary_key=True, serialize=False)),
                ("Timestamp", models.DateTimeField(auto_now_add=True)),
                ("LogContent", models.CharField(max_length=255)),
                ("Category", models.CharField(max_length=50)),
                (
                    "UserID",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="forum.useraccount",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("CommentID", models.AutoField(primary_key=True, serialize=False)),
                ("CommentContents", models.CharField(max_length=255)),
                ("Timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "PostID",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="forum.post"
                    ),
                ),
                (
                    "UserID",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="forum.useraccount",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("content_encrypted", models.TextField(blank=True, null=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="forum.chatsession",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="forum.useraccount",
                    ),
                ),
            ],
            options={
                "ordering": ["timestamp"],
            },
        ),
    ]
