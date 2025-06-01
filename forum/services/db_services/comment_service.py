from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
from .. import utilities
from datetime import datetime


# MARK: Insert Comment
def insert_new_comment(commentContents, postID, userID):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO forum_comment
                (CommentContents, Timestamp, PostID_id, UserID_id)
                VALUES (%s, %s, %s, %s);
                """,
                [commentContents, timestamp, postID, userID],
            )

        return utilities.response("SUCCESS", "Comment successfully created")

    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")


# MARK: Get Comments by ID
def get_comments_by_id(post_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM forum_comment WHERE CommentID = %s;;""",
                [post_id],
            )

            results = cursor.fetchall()
            columns = [
                "CommentID",
                "CommentContents",
                "Timestamp",
                "PostID_id",
                "UserID_id",
            ]
            comments = [dict(zip(columns, row)) for row in results]
            comment_data = {"comments": comments}

        return utilities.response("SUCCESS", "Retrieved Post for pages", comment_data)
    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")
