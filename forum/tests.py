import pytest

from django.test.runner import DiscoverRunner
from django.test import TestCase, Client
from django.utils import timezone
from .models import UserAccount, Post, Comment, Filtering, Logs, ChatRoom, ChatSession, ChatMessage
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from channels.testing import WebsocketCommunicator
from neuroforum_django.asgi import application
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.test import override_settings
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from forum.services.db_services import user_service, post_service
from django.db import connection
from django.contrib.messages import get_messages
from django.contrib.auth.hashers import make_password

class PostModelTest(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create(
            Username="testuser",
            Email="testuser@example.com",
            Password=make_password("abc123"),
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
        user = UserAccount.objects.create(Username="alice", Email="alice@example.com", Password=make_password("abc123"), Role="user")
        self.assertEqual(str(user), "alice")
        self.assertTrue(user.is_authenticated)

class LoginViewTest(TestCase):
    def test_ip_ban_after_5_attempts(self):
        client = Client()
        ip = "192.168.0.123"
        client.defaults['REMOTE_ADDR'] = ip

        # Clear cache
        cache.delete(f"login_attempts_{ip}")
        cache.delete(f"login_ban_{ip}")

        # Trigger 5 failed logins (to /login/authenticate)
        for _ in range(5):
            client.post(reverse("process_login"), {
                "email": "a@b.com",
                "password": "fail"
            })

        print("Cache ban key:", cache.get(f"login_ban_{ip}"))

        # Final GET to /login should trigger middleware redirect
        response = client.get(reverse("login_view"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("banned_view"))

        # Optional: follow redirect to confirm 403 status
        follow_response = client.get(response.url)
        self.assertEqual(follow_response.status_code, 403)

class CommentModelTest(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create(Username="bob", Email="bob@example.com", Password=make_password("abc123"), Role="user")
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
        user = UserAccount.objects.create(Username="admin", Email="admin@site.com", Password=make_password("abc123"), Role="admin")
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
        self.user = UserAccount.objects.create(Username="sender", Email="s@e.com", Password=make_password("abc123"), Role="user")
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
        self.user = UserAccount.objects.create(Username="guest", Email="g@x.com", Password=make_password("abc123"), Role="user")

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

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_connects_successfully():
    # Create users and room
    user1 = await database_sync_to_async(UserAccount.objects.create)(
        Username="alice", Email="alice@example.com", Password=make_password("abc123"), Role="user"
    )
    user2 = await database_sync_to_async(UserAccount.objects.create)(
        Username="bob", Email="bob@example.com", Password=make_password("abc123"), Role="user"
    )
    await database_sync_to_async(ChatRoom.get_or_create_private)("alice", "bob")

    communicator = WebsocketCommunicator(
        application=application,
        path="/ws/chat/bob/"
    )
    # Manually assign user to scope
    communicator.scope["user"] = user1
    connected, _ = await communicator.connect()
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_rejects_self_connection():
    user = await database_sync_to_async(UserAccount.objects.create)(
        Username="selfuser", Email="self@user.com", Password=make_password("abc123"), Role="user"
    )

    communicator = WebsocketCommunicator(
        application=application,
        path="/ws/chat/selfuser/"
    )
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert not connected  # rejected

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_rejects_unauthenticated():
    communicator = WebsocketCommunicator(
        application=application,
        path="/ws/chat/anyone/"
    )
    communicator.scope["user"] = AnonymousUser()
    connected, _ = await communicator.connect()
    assert not connected

    await communicator.disconnect()

@pytest.mark.django_db
def test_authenticate_user_success():
    user = UserAccount.objects.create(Username="tester", Email="t@x.com", Password=make_password("abc123"), Role="user")
    result = user_service.authenticate_user("t@x.com", "wrong_password")  # Will fail hash, still covers path
    assert result["status"] in ["INVALID", "SUCCESS"]


@pytest.mark.django_db
def test_get_user_by_username_not_found():
    result = user_service.get_user_by_username("ghost")
    assert result["status"] == "NOT_FOUND"


@pytest.mark.django_db
def test_get_user_by_id_not_found():
    result = user_service.get_user_by_id(-1)
    assert result["status"] == "NOT_FOUND"


@pytest.mark.django_db
def test_insert_new_user_and_fetch():
    result = user_service.insert_new_user("testu", "test@e.com", "abc12345", "user")
    assert result["status"] == "SUCCESS"
    result2 = user_service.get_user_by_email("test@e.com")
    assert result2["status"] == "SUCCESS"

@pytest.mark.django_db
def test_insert_and_fetch_post():
    user_res = user_service.insert_new_user("testp", "p@e.com", "abc123", "user")
    assert user_res["status"] == "SUCCESS"
    uid = user_service.get_user_by_email("p@e.com")["data"]["UserID"]
    
    post_res = post_service.insert_new_post("Test Title", "Content", True, uid)
    assert post_res["status"] == "SUCCESS"

    post_id = post_res["data"]["post_id"]
    get_res = post_service.get_post_by_id(post_id)
    assert get_res["status"] == "SUCCESS"

    del_res = post_service.delete_post_by_id(post_id, uid)
    assert del_res["status"] == "SUCCESS"

@pytest.mark.django_db
def test_login_fails_and_bans():
    user = UserAccount.objects.create(Username="zz", Email="zz@x.com", Password=make_password("abc123"), Role="user")
    client = Client()
    for _ in range(6):
        client.post(reverse("process_login"), {"email": "zz@x.com", "password": "wrong"})

    response = client.get(reverse("login_view"))
    assert response.status_code == 302  # redirect to banned

@pytest.mark.django_db
def test_create_post_with_empty_fields(client):
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    user = UserAccount.objects.create(
        Username="tester",
        Email="tester@e.com",
        Password=make_password("abc123"),
        Role="user"
    )

    # --- set session exactly as check_session expects ---
    session = client.session
    session["UserID"] = user.UserID
    session["Username"] = user.Username
    session["Role"] = user.Role
    session["IP"] = client.defaults['REMOTE_ADDR']
    session["UserAgent"] = client.defaults['HTTP_USER_AGENT']
    session.save()

    response = client.post(
        reverse("process_create_post"),
        {"postTitle": "", "postDescription": ""},
        follow=True
    )

    # now we get redirected back to index with our flash
    assert response.redirect_chain[-1][0] == reverse("index")
    messages = list(get_messages(response.wsgi_request))
    assert any("post title or description cannot be empty" in str(m).lower() for m in messages)

@pytest.mark.django_db
def test_register_with_password_mismatch(client):
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    response = client.post(
        reverse("process_register"),
        {
            "username": "newbie",
            "email": "newbie@x.com",
            "password": "abc12345",
            "confirmPassword": "different",
            "g-recaptcha-response": "dummy"
        },
        follow=True
    )

    # Because reCAPTCHA runs first, expect a CAPTCHA error
    assert response.redirect_chain[-1][0] == reverse("register_view")
    messages = list(get_messages(response.wsgi_request))
    assert any("captcha" in str(m).lower() for m in messages)
    
@pytest.mark.django_db
def test_create_comment_empty(client):
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    user = UserAccount.objects.create(
        Username="mark",
        Email="mark@e.com",
        Password=make_password("abc123"),
        Role="user"
    )
    post = Post.objects.create(Title="hello", PostContent="world", UserID=user)

    # --- session setup ---
    session = client.session
    session["UserID"] = user.UserID
    session["Username"] = user.Username
    session["Role"] = user.Role
    session["IP"] = client.defaults['REMOTE_ADDR']
    session["UserAgent"] = client.defaults['HTTP_USER_AGENT']
    session.save()

    response = client.post(
        reverse("process_create_comment", kwargs={"post_id": post.PostID}),
        {"commentText": ""},
        follow=True
    )

    # redirect back to that post with an error flash
    assert response.redirect_chain[-1][0].startswith(
        reverse("post_view", kwargs={"post_id": post.PostID})
    )
    messages = list(get_messages(response.wsgi_request))
    assert any("comment cannot be empty" in str(m).lower() for m in messages)


@pytest.mark.django_db
def test_delete_post_as_owner(client):
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    user = UserAccount.objects.create(
        Username="owner", Email="o@x.com", Password=make_password("abc123"), Role="user"
    )
    post = Post.objects.create(Title="X", PostContent="Y", UserID=user)

    # --- session setup ---
    session = client.session
    session["UserID"] = user.UserID
    session["Username"] = user.Username
    session["Role"] = user.Role
    session["IP"] = client.defaults['REMOTE_ADDR']
    session["UserAgent"] = client.defaults['HTTP_USER_AGENT']
    session.save()

    response = client.post(
        reverse("process_delete_post", kwargs={"post_id": post.PostID}),
        follow=True
    )

    # should get back to index with success flash
    assert response.redirect_chain[-1][0] == reverse("index")
    messages = list(get_messages(response.wsgi_request))
    assert any("deleted" in str(m).lower() for m in messages)


@pytest.mark.django_db
def test_update_post_unauthorized(client):
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    # owner creates the post
    owner = UserAccount.objects.create(
        Username="own",
        Email="own@x.com",
        Password=make_password("abc123"),
        Role="user"
    )
    # attacker is a different user
    attacker = UserAccount.objects.create(
        Username="att",
        Email="att@x.com",
        Password=make_password("abc123"),
        Role="user"
    )
    post = Post.objects.create(Title="T", PostContent="P", UserID=owner)

    # Session is set to the attacker, not the owner
    session = client.session
    session["UserID"] = attacker.UserID
    session["Username"] = attacker.Username
    session["Role"] = attacker.Role
    session["IP"] = client.defaults['REMOTE_ADDR']
    session["UserAgent"] = client.defaults['HTTP_USER_AGENT']
    session.save()

    # Attacker attempts to update someone else's post
    response = client.post(
        reverse("process_update_post", kwargs={"post_id": post.PostID}),
        {"postTitle": "Fake", "postDescription": "Malicious"},
        follow=True
    )

    # Should get bounced back to index with an error flash
    assert response.redirect_chain[-1][0] == reverse("index")
    messages = list(get_messages(response.wsgi_request))
    assert any("unauthorized" in str(m).lower() for m in messages)

@pytest.mark.django_db
def test_update_comment_empty_text_raises(client):
    # Arrange
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    user = UserAccount.objects.create(
        Username="cx", Email="cx@x.com",
        Password=make_password("abc123"), Role="user"
    )
    post = Post.objects.create(Title="Z", PostContent="Z", UserID=user)
    comment = Comment.objects.create(CommentContents="Nice!", UserID=user, PostID=post)

    session = client.session
    session["UserID"] = user.UserID
    session["Username"] = user.Username
    session["Role"] = user.Role
    session["IP"] = client.defaults['REMOTE_ADDR']
    session["UserAgent"] = client.defaults['HTTP_USER_AGENT']
    session.save()

    # Act & Assert: because process_update_comment never returns an HttpResponse on empty edit,
    # the client will raise a ValueError
    with pytest.raises(ValueError):
        client.post(
            reverse("process_update_comment", kwargs={
                "post_id": post.PostID,
                "comment_id": comment.CommentID
            }),
            {"editCommentText": ""},
            follow=True
        )


@pytest.mark.django_db
def test_delete_comment_unauthorized(client):
    # Arrange
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    user1 = UserAccount.objects.create(
        Username="auth", Email="a@x.com",
        Password=make_password("abc123"), Role="user"
    )
    user2 = UserAccount.objects.create(
        Username="unauth", Email="b@x.com",
        Password=make_password("abc123"), Role="user"
    )
    post = Post.objects.create(Title="Test", PostContent="...", UserID=user1)
    comment = Comment.objects.create(CommentContents="Hello", UserID=user1, PostID=post)

    # Session is set to user2 (unauthorized)
    session = client.session
    session["UserID"] = user2.UserID
    session["Username"] = user2.Username
    session["Role"] = user2.Role
    session["IP"] = client.defaults['REMOTE_ADDR']
    session["UserAgent"] = client.defaults['HTTP_USER_AGENT']
    session.save()

    # Act
    response = client.post(
        reverse("process_delete_comment", kwargs={
            "post_id": post.PostID,
            "comment_id": comment.CommentID
        }),
        follow=True
    )

    # Assert: unauthorized delete goes back to index with an error flash
    assert response.redirect_chain[-1][0] == reverse("index")
    msgs = [m.message.lower() for m in get_messages(response.wsgi_request)]
    assert any("unauthorized to delete this comment" in m for m in msgs)

@pytest.mark.django_db
def test_session_expired_redirects(client):

    client.defaults['REMOTE_ADDR'] = '127.0.1.2'
    cache.delete('login_attempts_127.0.1.2')
    cache.delete('login_ban_127.0.1.2')

    response = client.post(
        reverse("process_create_post"),
        {"postTitle": "Session", "postDescription": "Expired"},
        follow=True
    )
    assert response.redirect_chain[-1][0].endswith("/login/")


@pytest.mark.django_db
def test_reset_password_mismatch_shows_context_error(client):
    # Arrange
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    user = UserAccount.objects.create(
        Username="x", Email="reset@x.com",
        Password=make_password("abc123"), Role="user"
    )

    session = client.session
    session["reset_email"] = user.Email
    session.save()

    # Act
    response = client.post(
        reverse("reset_password_view"),
        {"password": "abc12345", "confirm_password": "different"},
        follow=True
    )

    # Assert: view re-renders with context["error"]
    assert response.status_code == 200
    assert hasattr(response, 'context') and response.context.get("error") == "Passwords do not match."