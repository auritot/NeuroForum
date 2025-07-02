import xmlrunner
from django.test.runner import DiscoverRunner
from django.test import TestCase, Client
from django.utils import timezone
from .models import UserAccount, Post, Comment, Filtering, Logs, ChatRoom, ChatSession, ChatMessage
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache

test_runner = xmlrunner.XMLTestRunner(output=settings.TEST_OUTPUT_DIR)


class PostModelTest(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create(
            Username="testuser",
            Email="testuser@example.com",
            Password="securepassword123",
            Role="user"
        )
        self.post = Post.objects.create(
            Title="Test Post",
            PostContent="This is a test post content.",
            UserID=self.user
        )

    def test_post_created_successfully(self):
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(self.post.Title, "Test Post")
        self.assertEqual(self.post.UserID.Username, "testuser")

    def test_post_string_representation(self):
        self.assertEqual(str(self.post), "Test Post")


class UserAccountModelTest(TestCase):
    def test_user_creation_and_auth(self):
        user = UserAccount.objects.create(Username="alice", Email="alice@example.com", Password="pwd123", Role="user")
        self.assertEqual(str(user), "alice")
        self.assertTrue(user.is_authenticated)

class LoginViewTest(TestCase):
    def test_ip_ban_after_5_attempts(self):
        client = Client()
        ip = "192.168.0.123"

        # Clear previous attempts if test reuses cache
        cache.delete(f"login_attempts_{ip}")
        cache.delete(f"login_ban_{ip}")

        for _ in range(5):
            client.post(reverse("login_view"), {
                "email": "a@b.com",
                "password": "fail"
            }, REMOTE_ADDR=ip)

        response = client.get(reverse("login_view"), REMOTE_ADDR=ip)
        self.assertRedirects(response, reverse("banned_view"))

class CommentModelTest(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create(Username="bob", Email="bob@example.com", Password="pwd", Role="user")
        self.post = Post.objects.create(Title="Sample", PostContent="Post", UserID=self.user)

    def test_comment_creation(self):
        comment = Comment.objects.create(CommentContents="Nice!", UserID=self.user, PostID=self.post)
        self.assertIn("Comment", str(comment))


class FilteringModelTest(TestCase):
    def test_filter_word(self):
        word = Filtering.objects.create(FilterContent="banned")
        self.assertEqual(str(word), "banned")


class LogsModelTest(TestCase):
    def test_log_entry(self):
        user = UserAccount.objects.create(Username="admin", Email="admin@site.com", Password="root", Role="admin")
        log = Logs.objects.create(LogContent="Login detected", Category="auth", UserID=user)
        self.assertIn("Login detected", str(log))


class ChatRoomTest(TestCase):
    def test_room_creation(self):
        room = ChatRoom.objects.create(name="test_room")
        self.assertEqual(str(room), "test_room")

    def test_private_room_generation(self):
        room = ChatRoom.get_or_create_private("alice", "bob")
        self.assertTrue(room.name.startswith("private_"))


class ChatSessionMessageTest(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create(Username="sender", Email="s@e.com", Password="x", Role="user")
        self.room = ChatRoom.objects.create(name="roomx")
        self.session = ChatSession.objects.create(room=self.room)

    def test_chat_message_encrypt_decrypt(self):
        msg = ChatMessage.objects.create(session=self.session, sender=self.user)
        msg.content = "hello"
        msg.save()
        self.assertEqual(msg.content, "hello")

    def test_session_repr(self):
        self.assertIn("Open since", str(self.session))


class ViewTestBasic(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserAccount.objects.create(Username="guest", Email="g@x.com", Password="p", Role="user")

    def test_index_loads(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    def test_register_view(self):
        response = self.client.get(reverse("register_view"))
        self.assertContains(response, settings.RECAPTCHA_PUBLIC_KEY)

    def test_login_view(self):
        response = self.client.get(reverse("login_view"))
        self.assertContains(response, "Login")

    def test_forgot_password_view_get(self):
        response = self.client.get(reverse("forgot_password_view"))
        self.assertEqual(response.status_code, 200)

    def test_reset_password_view_get(self):
        session = self.client.session
        session["reset_email"] = self.user.Email
        session.save()
        response = self.client.get(reverse("reset_password_view"))
        self.assertEqual(response.status_code, 200)
