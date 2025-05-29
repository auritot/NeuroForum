from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
from . import utilities
from datetime import datetime


# MARK: Login Authentication
def authenticate_user(email, password):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ SELECT * FROM forum_useraccount WHERE Email = %s; """,
                [email],
            )

            result = cursor.fetchone()
            if result is None:
                return utilities.response("NOT_FOUND", "User not found")

            user_data = {
                "UserID": result[0],
                "Username": result[1],
                "Email": result[2],
                "Password": result[3],
                "Role": result[4],
            }

            if not check_password(password, user_data["Password"]):
                return utilities.response("INVALID", "User login was unsuccessfully")

        return utilities.response("SUCCESS", "User login was successfully", user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


# MARK: User Registration
def insert_new_user(username, email, password, role, emailVerificationCode):
    try:
        hash_password = make_password(password)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO forum_useraccount (Username, Email, Password, Role, EmailVerificationCode)
                VALUES (%s, %s, %s, %s, %s);
                """,
                [username, email, hash_password, role, emailVerificationCode],
            )

        return utilities.response("SUCCESS", "User account successfully created")

    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")


# MARK: Get Total Posts
def get_total_post_count():
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT COUNT(*) FROM forum_post""")

            result = cursor.fetchone()
            total_posts = result[0] if result else 0
            post_data = {"total_post": total_posts}

        return utilities.response("SUCCESS", "Retrieved Total Post Count", post_data)
    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")


# MARK: Get Posts for pages
def get_posts_by_pages(start_index, per_page):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM forum_post LIMIT %s, %s;""", [start_index, per_page]
            )

            results = cursor.fetchall()
            columns = [
                "PostID",
                "Title",
                "PostContent",
                "Timestamp",
                "CommentStatus",
                "UserID_id",
            ]
            posts = [dict(zip(columns, row)) for row in results]
            post_data = {"posts": posts}

        return utilities.response("SUCCESS", "Retrieved Post for pages", post_data)
    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")


# MARK: Get Posts by ID
def get_posts_by_id(post_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT * FROM forum_post WHERE PostID = %s;""", [post_id])

            result = cursor.fetchone()
            if result is None:
                return utilities.response("NOT_FOUND", "Post not found")

            columns = [
                "PostID",
                "Title",
                "PostContent",
                "Timestamp",
                "CommentStatus",
                "UserID_id",
            ]

            post = dict(zip(columns, result))
            post_data = {"post": post}

        return utilities.response("SUCCESS", "Retrieved Post for pages", post_data)
    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")


# MARK: Insert Post
def insert_new_post(postTitle, postDescription, allowComments, userID):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        commentStatus = 1 if allowComments else 0

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO forum_post
                (Title, PostContent, Timestamp, CommentStatus, UserID_id)
                VALUES (%s, %s, %s, %s, %s);
                """,
                [postTitle, postDescription, timestamp, commentStatus, userID],
            )

            # cursor.execute("SELECT LAST_INSERT_ID();")
            # result = cursor.fetchone()
            # if result is None:
            #     return utilities.response("NOT_FOUND", "Post not found ")

            # postID = {"post_id": result[0]}
        return utilities.response("SUCCESS", "Post successfully created")

    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")
