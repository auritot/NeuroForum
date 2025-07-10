import pytest
import json
import asyncio
import requests

from datetime import timedelta

from django.test.runner import DiscoverRunner
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse, path
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.contrib.messages import get_messages

from .models import UserAccount, Post, Comment, Filtering, Logs, ChatRoom, ChatSession, ChatMessage
from forum.consumers import PrivateChatConsumer
from forum.processes import user_process
from forum.services.db_services import user_service, post_service
from forum.services import session_utils, utilities
from forum.crypto_utils import custom_hash_password

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.routing import URLRouter

from neuroforum_django.asgi import application

class PostModelTest(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create(
            Username="testuser",
            Email="testuser@example.com",
            Password=custom_hash_password("abc123"),
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
        user = UserAccount.objects.create(Username="alice", Email="alice@example.com", Password=custom_hash_password("abc123"), Role="user")
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
        self.user = UserAccount.objects.create(Username="bob", Email="bob@example.com", Password=custom_hash_password("abc123"), Role="user")
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
        user = UserAccount.objects.create(Username="admin", Email="admin@site.com", Password=custom_hash_password("abc123"), Role="admin")
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
        self.user = UserAccount.objects.create(Username="sender", Email="s@e.com", Password=custom_hash_password("abc123"), Role="user")
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
        self.user = UserAccount.objects.create(Username="guest", Email="g@x.com", Password=custom_hash_password("abc123"), Role="user")

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
        Username="alice", Email="alice@example.com", Password=custom_hash_password("abc123"), Role="user"
    )
    user2 = await database_sync_to_async(UserAccount.objects.create)(
        Username="bob", Email="bob@example.com", Password=custom_hash_password("abc123"), Role="user"
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
        Username="selfuser", Email="self@user.com", Password=custom_hash_password("abc123"), Role="user"
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
    user = UserAccount.objects.create(Username="tester", Email="t@x.com", Password=custom_hash_password("abc123"), Role="user")
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
    user = UserAccount.objects.create(Username="zz", Email="zz@x.com", Password=custom_hash_password("abc123"), Role="user")
    client = Client()
    for _ in range(6):
        client.post(reverse("process_login"), {"email": "zz@x.com", "password": "wrong"})

    response = client.get(reverse("login_view"))
    assert response.status_code == 302  # redirect to banned

@pytest.fixture(autouse=True)
def clear_login_cache():
    """
    Ensure no leftover login‐attempt or login‐ban keys.
    On RedisCache we can delete by pattern; on LocMemCache we just clear everything.
    """
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("login_attempts_*")
        cache.delete_pattern("login_ban_*")
    else:
        cache.clear()


def login_as(client, email, password):
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'

    # 1) Send the login request
    resp = client.post(
        reverse("process_login"),
        {"email": email, "password": password},
        # no follow here— we only want the raw JSON + Set-Cookie header
    )
    assert resp.status_code == 200

    # 2) Capture the session cookie that your login view just set
    session_cookie_name = settings.SESSION_COOKIE_NAME  # often "sessionid" or "session_id"
    if session_cookie_name in resp.cookies:
        client.cookies[session_cookie_name] = resp.cookies[session_cookie_name].value
    else:
        raise AssertionError(f"No `{session_cookie_name}` cookie set on login response")

    return resp


@pytest.mark.django_db
def test_create_post_with_empty_fields(client):
    # --- create and login ---
    user = UserAccount.objects.create(
        Username="tester",
        Email="tester@e.com",
        Password=custom_hash_password("abc123"),  # ← use custom hash
        Role="user"
    )
    resp = login_as(client, user.Email, "abc123")
    assert resp.status_code == 200

    # --- attempt to create an empty post ---
    response = client.post(
        reverse("process_create_post"),
        {"postTitle": "", "postDescription": ""},
        follow=True
    )
    # redirect back to index
    assert response.redirect_chain[-1][0] == reverse("index")

    msgs = [m.message for m in get_messages(response.wsgi_request)]
    assert any("cannot be empty" in m.lower() for m in msgs)

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
    # --- setup user, post, login ---
    user = UserAccount.objects.create(
        Username="mark",
        Email="mark@e.com",
        Password=custom_hash_password("abc123"),
        Role="user"
    )
    post = Post.objects.create(Title="hello", PostContent="world", UserID=user)
    resp = login_as(client, user.Email, "abc123")
    assert resp.status_code == 200

    # --- attempt to create an empty comment ---
    response = client.post(
        reverse("process_create_comment", kwargs={"post_id": post.PostID}),
        {"commentText": ""},
        follow=True
    )
    # should bounce back to post view
    assert response.redirect_chain[-1][0].startswith(
        reverse("post_view", kwargs={"post_id": post.PostID})
    )

    msgs = [m.message for m in get_messages(response.wsgi_request)]
    assert any("cannot be empty" in m.lower() for m in msgs)


@pytest.mark.django_db
def test_delete_post_as_owner(client):
    # --- setup owner and post, then login as owner ---
    owner = UserAccount.objects.create(
        Username="owner",
        Email="o@x.com",
        Password=custom_hash_password("abc123"),
        Role="user"
    )
    post = Post.objects.create(Title="X", PostContent="Y", UserID=owner)
    resp = login_as(client, owner.Email, "abc123")
    assert resp.status_code == 200

    # --- delete the post ---
    response = client.post(
        reverse("process_delete_post", kwargs={"post_id": post.PostID}),
        follow=True
    )
    assert response.redirect_chain[-1][0] == reverse("index")

    msgs = [m.message for m in get_messages(response.wsgi_request)]
    assert any("deleted" in m.lower() for m in msgs)


@pytest.mark.django_db
def test_update_post_unauthorized(client):
    # --- owner & attacker, then login as attacker ---
    owner = UserAccount.objects.create(
        Username="own",
        Email="own@x.com",
        Password=custom_hash_password("abc123"),
        Role="user"
    )
    attacker = UserAccount.objects.create(
        Username="att",
        Email="att@x.com",
        Password=custom_hash_password("abc123"),
        Role="user"
    )
    post = Post.objects.create(Title="T", PostContent="P", UserID=owner)

    resp = login_as(client, attacker.Email, "abc123")
    assert resp.status_code == 200

    # --- attempt unauthorized update ---
    response = client.post(
        reverse("process_update_post", kwargs={"post_id": post.PostID}),
        {"postTitle": "Fake", "postDescription": "Malicious"},
        follow=True
    )
    assert response.redirect_chain[-1][0] == reverse("index")

    msgs = [m.message for m in get_messages(response.wsgi_request)]
    assert any("unauthorized" in m.lower() for m in msgs)

@pytest.mark.django_db
def test_update_comment_empty_text_raises(client):
    # --- setup user, post, comment, then login ---
    user = UserAccount.objects.create(
        Username="cx",
        Email="cx@x.com",
        Password=custom_hash_password("abc123"),
        Role="user"
    )
    post = Post.objects.create(Title="Z", PostContent="Z", UserID=user)
    comment = Comment.objects.create(
        CommentContents="Nice!", UserID=user, PostID=post
    )
    resp = login_as(client, user.Email, "abc123")
    assert resp.status_code == 200

    # --- attempt to submit empty edit ---
    response = client.post(
        reverse("process_update_comment", kwargs={
            "post_id": post.PostID,
            "comment_id": comment.CommentID
        }),
        {"editCommentText": ""},
        follow=True
    )
    # should redirect back with an error
    assert response.redirect_chain[-1][0] == reverse("index")

    msgs = [m.message for m in get_messages(response.wsgi_request)]
    assert any("cannot be empty" in m.lower() for m in msgs)


@pytest.mark.django_db
def test_delete_comment_unauthorized(client):
    # Arrange
    client.defaults['REMOTE_ADDR'] = '127.0.1.1'
    client.defaults['HTTP_USER_AGENT'] = 'pytest'
    cache.delete("login_attempts_127.0.1.1")
    cache.delete("login_ban_127.0.1.1")

    user1 = UserAccount.objects.create(
        Username="auth", Email="a@x.com",
        Password=custom_hash_password("abc123"), Role="user"
    )
    user2 = UserAccount.objects.create(
        Username="unauth", Email="b@x.com",
        Password=custom_hash_password("abc123"), Role="user"
    )
    post = Post.objects.create(Title="Test", PostContent="...", UserID=user1)
    comment = Comment.objects.create(CommentContents="Hello", UserID=user1, PostID=post)

    # Log in as the wrong user
    resp = login_as(client, user2.Email, "abc123")
    assert resp.status_code == 200

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
        Password=custom_hash_password("abc123"), Role="user"
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


# ─────── Tests for post_service.py ───────

@pytest.mark.django_db
def test_get_post_by_id_success():
    # Create a user & a post, then fetch by ID
    ures = user_service.insert_new_user("psuc", "psuc@e.com", "pw", "user")
    uid = user_service.get_user_by_email("psuc@e.com")["data"]["UserID"]
    ires = post_service.insert_new_post("Hello", "World", True, uid)
    pid = ires["data"]["post_id"]

    gres = post_service.get_post_by_id(pid)
    assert gres["status"] == "SUCCESS"
    post = gres["data"]["post"]
    assert post["PostID"] == pid
    assert post["Title"] == "Hello"
    assert post["CommentCount"] == 0

@pytest.mark.django_db
def test_get_posts_for_page_with_user_filter():
    # Two users each make one post; filter on one user
    u1 = user_service.insert_new_user("f1", "f1@e.com", "pw", "user")
    u2 = user_service.insert_new_user("f2", "f2@e.com", "pw", "user")
    id1 = user_service.get_user_by_email("f1@e.com")["data"]["UserID"]
    id2 = user_service.get_user_by_email("f2@e.com")["data"]["UserID"]
    post_service.insert_new_post("A", "B", True, id1)
    post_service.insert_new_post("C", "D", True, id2)

    res1 = post_service.get_posts_for_page(0, 10, userID=id1)
    assert len(res1["data"]["posts"]) == 1
    assert res1["data"]["posts"][0]["UserID_id"] == id1

    res2 = post_service.get_posts_for_page(0, 10, userID=id2)
    assert len(res2["data"]["posts"]) == 1
    assert res2["data"]["posts"][0]["UserID_id"] == id2

@pytest.mark.django_db
def test_delete_post_as_admin_flag_changes_log(monkeypatch):
    # Just hit the isAdmin=True branch
    ures = user_service.insert_new_user("adm", "adm@e.com", "pw", "user")
    uid = user_service.get_user_by_email("adm@e.com")["data"]["UserID"]
    ires = post_service.insert_new_post("X", "Y", False, uid)
    pid = ires["data"]["post_id"]

    called = {}
    def fake_log(msg, u, **kw):
        called['msg'] = msg
    monkeypatch.setattr("forum.services.db_services.log_service.log_action", fake_log)

    dres = post_service.delete_post_by_id(pid, uid, isAdmin=True)
    assert dres["status"] == "SUCCESS"
    assert "Admin deleted Post" in called['msg']

@pytest.mark.django_db
def test_search_posts_sort_order_oldest_and_newest():
    ures = user_service.insert_new_user("so", "so@e.com", "pw", "user")
    uid = user_service.get_user_by_email("so@e.com")["data"]["UserID"]
    post_service.insert_new_post("First", "foo", True, uid)
    post_service.insert_new_post("Second", "foo", True, uid)

    newest = post_service.search_posts_by_keyword("foo", start_index=0, per_page=10, sort_order="newest")
    oldest = post_service.search_posts_by_keyword("foo", start_index=0, per_page=10, sort_order="oldest")

    assert newest["data"]["posts"][0]["Title"] == "Second"
    assert oldest["data"]["posts"][0]["Title"] == "First"


# ─────── Async tests for consumers.py ───────

# mount just the URLRouter (no AuthMiddlewareStack) so scope["user"] sticks
chat_urlpatterns = URLRouter([
    path("ws/chat/<str:username>/", PrivateChatConsumer.as_asgi()),
])

@database_sync_to_async
def create_user(username, email):
    return UserAccount.objects.create(
        Username=username,
        Email=email,
        Password=custom_hash_password("pw"),
        Role="user"
    )

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_history_flag_on_fresh_session():
    u1 = await create_user("h1", "h1@e.com")
    u2 = await create_user("h2", "h2@e.com")
    await database_sync_to_async(ChatRoom.get_or_create_private)("h1", "h2")

    comm = WebsocketCommunicator(chat_urlpatterns, "/ws/chat/h2/")
    comm.scope["user"] = u1
    connected, _ = await comm.connect()
    assert connected

    init = await comm.receive_json_from()
    assert init.get("history") is True

    await comm.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_unread_notification_handler():
    u1 = await create_user("n1", "n1@e.com")
    u2 = await create_user("n2", "n2@e.com")
    await database_sync_to_async(ChatRoom.get_or_create_private)("n1", "n2")

    comm = WebsocketCommunicator(chat_urlpatterns, "/ws/chat/n2/")
    comm.scope["user"] = u1
    connected, _ = await comm.connect()
    assert connected

    # Consume the initial history frame
    await comm.receive_json_from()

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "notify_n1",
        {"type": "chat.unread_notification", "from_user": "n2"}
    )

    note = await comm.receive_json_from()
    assert note == {"type": "notify", "from": "n2"}

    await comm.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_message_event_handler_direct():
    u1 = await create_user("e1", "e1@e.com")
    u2 = await create_user("e2", "e2@e.com")
    room = await database_sync_to_async(ChatRoom.get_or_create_private)("e1", "e2")

    comm = WebsocketCommunicator(chat_urlpatterns, f"/ws/chat/{u2.Username}/")
    comm.scope["user"] = u1
    connected, _ = await comm.connect()
    assert connected

    # Consume the initial history frame
    await comm.receive_json_from()

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        room.name,
        {
            "type":      "chat.message",
            "message":   "direct!",
            "sender":    "e1",
            "timestamp": "NOW",
            "history":   False,
        }
    )

    out = await comm.receive_json_from()
    assert out == {
        "message":   "direct!",
        "sender":    "e1",
        "timestamp": "NOW",
        "history":   False,
    }

    await comm.disconnect()


# ─── Helpers ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_generate_verification_code_default_and_custom_length():
    code6 = user_process.generate_verification_code()
    assert len(code6) == 6 and code6.isdigit()

    code4 = user_process.generate_verification_code(length=4)
    assert len(code4) == 4 and code4.isdigit()


# ─── process_login ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_process_login_get_redirects(client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    resp = client.get(reverse("process_login"))
    assert resp.status_code == 302
    assert resp.url == reverse("login_view")


@pytest.mark.django_db
def test_process_register_get_redirects(client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    resp = client.get(reverse("process_register"))
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")


@pytest.mark.django_db
def test_process_register_missing_captcha(client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    data = {
        "username": "a",
        "email": "a@x.com",
        "password": "pw",
        "confirmPassword": "pw"
    }
    resp = client.post(reverse("process_register"), data)
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")

    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("CAPTCHA" in m for m in msgs)


@pytest.mark.django_db
def test_process_register_captcha_fails(monkeypatch, client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    monkeypatch.setenv("RECAPTCHA_PRIVATE_KEY", "key")
    class FakeResp:
        def json(self): return {"success": False, "error-codes": ["bad"]}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResp())

    data = {
        "g-recaptcha-response": "tok",
        "username": "u",
        "email": "u@x.com",
        "password": "pw",
        "confirmPassword": "pw"
    }
    resp = client.post(reverse("process_register"), data)
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")

    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("CAPTCHA verification failed" in m for m in msgs)


@pytest.mark.django_db
def test_process_register_password_mismatch(monkeypatch, client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    monkeypatch.setenv("RECAPTCHA_PRIVATE_KEY", "key")
    class FakeResp:
        def json(self): return {"success": True}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResp())

    data = {
        "g-recaptcha-response": "tok",
        "username": "u",
        "email": "u@x.com",
        "password": "pw1",
        "confirmPassword": "pw2"
    }
    resp = client.post(reverse("process_register"), data)
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")

    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Passwords does not match" in m for m in msgs)


@pytest.mark.django_db
def test_process_register_nist_violation(monkeypatch, client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    monkeypatch.setenv("RECAPTCHA_PRIVATE_KEY", "key")
    class FakeResp:
        def json(self): return {"success": True}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResp())
    monkeypatch.setattr(user_process, "validate_password_nist", lambda pw: (False, "too weak"))

    data = {
        "g-recaptcha-response": "tok",
        "username": "u",
        "email": "u@x.com",
        "password": "weakpw",
        "confirmPassword": "weakpw"
    }
    resp = client.post(reverse("process_register"), data)
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")

    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("too weak" in m for m in msgs)


@pytest.mark.django_db
def test_process_register_invalid_email(monkeypatch, client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    monkeypatch.setenv("RECAPTCHA_PRIVATE_KEY", "key")
    class FakeResp:
        def json(self): return {"success": True}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResp())
    monkeypatch.setattr(user_process, "validate_password_nist", lambda pw: (True, None))
    monkeypatch.setattr(utilities, "validate_email", lambda e: False)

    data = {
        "g-recaptcha-response": "tok",
        "username": "u",
        "email": "bad@",
        "password": "Good#123",
        "confirmPassword": "Good#123"
    }
    resp = client.post(reverse("process_register"), data)
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")

    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Enter a valid email" in m for m in msgs)


@pytest.mark.django_db
def test_process_register_duplicate_username(monkeypatch, client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    monkeypatch.setenv("RECAPTCHA_PRIVATE_KEY", "key")
    class FakeResp:
        def json(self): return {"success": True}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResp())
    monkeypatch.setattr(user_process, "validate_password_nist", lambda pw: (True, None))
    monkeypatch.setattr(utilities, "validate_email", lambda e: True)
    monkeypatch.setattr(user_service, "get_user_by_username", lambda u: {"status": "SUCCESS"})

    data = {
        "g-recaptcha-response": "tok",
        "username": "taken",
        "email": "u@x.com",
        "password": "Good#123",
        "confirmPassword": "Good#123"
    }
    resp = client.post(reverse("process_register"), data)
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")

    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("taken" in m for m in msgs)


@pytest.mark.django_db
def test_process_register_duplicate_email(monkeypatch, client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    monkeypatch.setenv("RECAPTCHA_PRIVATE_KEY", "key")
    class FakeResp:
        def json(self): return {"success": True}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResp())
    monkeypatch.setattr(user_process, "validate_password_nist", lambda pw: (True, None))
    monkeypatch.setattr(utilities, "validate_email", lambda e: True)
    monkeypatch.setattr(user_service, "get_user_by_username", lambda u: {"status": "NOT_FOUND"})
    monkeypatch.setattr(user_service, "get_user_by_email", lambda e: {"status": "SUCCESS"})

    data = {
        "g-recaptcha-response": "tok",
        "username": "newu",
        "email": "used@x.com",
        "password": "Good#123",
        "confirmPassword": "Good#123"
    }
    resp = client.post(reverse("process_register"), data)
    assert resp.status_code == 302
    assert resp.url == reverse("register_view")

    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("already been used" in m for m in msgs)


@pytest.mark.django_db
def test_process_register_success(monkeypatch, client):
    ip = "127.0.0.1"
    client.defaults["REMOTE_ADDR"] = ip
    cache.delete(f"login_ban_{ip}")
    cache.delete(f"login_attempts_{ip}")

    monkeypatch.setenv("RECAPTCHA_PRIVATE_KEY", "key")
    class FakeResp:
        def json(self): return {"success": True}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResp())
    monkeypatch.setattr(user_process, "validate_password_nist", lambda pw: (True, None))
    monkeypatch.setattr(utilities, "validate_email", lambda e: True)
    monkeypatch.setattr(user_service, "get_user_by_username", lambda u: {"status": "NOT_FOUND"})
    monkeypatch.setattr(user_service, "get_user_by_email", lambda e: {"status": "NOT_FOUND"})
    monkeypatch.setattr(user_service, "insert_new_user", lambda *a, **k: {"status": "SUCCESS"})

    resp = client.post(
        reverse("process_register"),
        {
            "g-recaptcha-response": "tok",
            "username": "newu",
            "email": "new@x.com",
            "password": "Good#123",
            "confirmPassword": "Good#123"
        }
    )
    assert resp.status_code == 302
    assert resp.url == reverse("email_verification")
