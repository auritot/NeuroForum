from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
from .. import utilities
from datetime import datetime

post_username_comment_count_col = ["PostID", "Title", "PostContent", "Timestamp", "CommentStatus", "UserID_id", "Username", "CommentCount"]

# MARK: Get Total Post Count
def get_total_post_count():
    try:
        with connection.cursor() as cursor:
            cursor.execute(""" SELECT COUNT(*) FROM forum_post; """)

            result = cursor.fetchone()
            total_post_count = result[0] if result else 0
            post_data = {"total_post_count": total_post_count}

        return utilities.response("SUCCESS", "Retrieved Total Post Count", post_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


# MARK: Get Posts for pages
def get_posts_by_pages(start_index, per_page):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.*, u.Username, COUNT(c.CommentID) AS CommentCount
                FROM forum_post p
                JOIN forum_useraccount u ON p.UserID_id = u.UserID
                LEFT JOIN forum_comment c ON c.PostID_id = p.PostID
                GROUP BY p.PostID, u.UserID
                ORDER BY p.Timestamp DESC;
                LIMIT %s, %s;
                """, 
                [start_index, per_page],
            )

            results = cursor.fetchall()
            posts = [dict(zip(post_username_comment_count_col, row)) for row in results]
            post_data = {"posts": posts}

        return utilities.response("SUCCESS", "Retrieved Post for pages", post_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


# MARK: Get Post by ID
def get_post_by_id(postID):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.*, u.Username, COUNT(c.CommentID) AS CommentCount
                FROM forum_post p
                JOIN forum_useraccount u ON p.UserID_id = u.UserID
                LEFT JOIN forum_comment c ON c.PostID_id = p.PostID
                WHERE PostID = %s;
                GROUP BY p.PostID, u.UserID
                """, 
                [postID],
            )

            result = cursor.fetchone()
            if result is None:
                return utilities.response("NOT_FOUND", "Post not found")

            post = dict(zip(post_username_comment_count_col, result))
            post_data = {"post": post}

        return utilities.response("SUCCESS", "Retrieved Post for pages", post_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


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

        return utilities.response("SUCCESS", "Post successfully created")

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Delete Post by ID
def delete_post_by_id(postID):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ DELETE FROM forum_comment WHERE PostID_id = %s; """,
                [postID],
            )

            cursor.execute(
                """ DELETE FROM forum_post WHERE PostID = %s; """,
                [postID],
            )

        return utilities.response("SUCCESS", "Post and Comments deleted successfully")
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Update Post by ID
def update_post_by_id(postTitle, postDescription, allowComments, postID):
    try:
        commentStatus = 1 if allowComments else 0

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE forum_post
                SET Title = %s, PostContent = %s, CommentStatus = %s 
                WHERE PostID = %s;
                """,
                [postTitle, postDescription, commentStatus, postID],
            )

        return utilities.response("SUCCESS", "Post updated successfully")
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")