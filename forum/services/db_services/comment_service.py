from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
from .. import utilities
from datetime import datetime

comment_username_col = ["CommentID", "CommentContents", "Timestamp", "PostID_id", "UserID_id", "Username"]

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


# MARK: Get Comments by Post ID
def get_comments_by_post_id(post_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.*, u.Username FROM forum_comment c
                JOIN forum_useraccount u ON c.UserID_id = u.UserID
                WHERE c.PostID_id = %s
                ORDER BY c.Timestamp DESC;
                """,
                [post_id],
            )

            results = cursor.fetchall()
            comments = [dict(zip(comment_username_col, row)) for row in results]
            comment_data = {"comments": comments}

        return utilities.response("SUCCESS", "Retrieved Post for pages", comment_data)
    except Exception as e:
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")
