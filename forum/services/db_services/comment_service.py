from django.db import connection, transaction
from django.contrib.auth.hashers import check_password, make_password
from .. import utilities
from datetime import datetime

comment_col = ["CommentID", "CommentContents", "Timestamp", "PostID_id", "UserID_id"]
comment_username_col = ["CommentID", "CommentContents", "Timestamp", "PostID_id", "UserID_id", "Username", "CommentPosition"]

# MARK: Get Comments for page by Post ID
def get_comments_for_page(start_index, per_page, postID=None, userID=None):
    base_query = """
                SELECT c.*, u.Username,
                (
                    SELECT COUNT(*) + 1 FROM forum_comment c2
                    WHERE c2.PostID_id = c.PostID_id AND c2.Timestamp > c.Timestamp
                    ORDER BY c.Timestamp DESC
                ) AS CommentPosition
                """
    where_clauses = []
    params = []

    if userID:
        base_query += """,
                    CEIL((
                        SELECT COUNT(*) + 1 FROM forum_comment c2
                        WHERE c2.PostID_id = c.PostID_id AND c2.Timestamp > c.Timestamp
                        ORDER BY c.Timestamp DESC
                    ) / %s) AS PageNumberInPost
                    """
        params.append(per_page)
        comment_username_col.append("PageNumberInPost")
        
        where_clauses.append("c.UserID_id = %s")
        params.append(userID)

    if postID:
        where_clauses.append("c.PostID_id = %s")
        params.append(postID)

    base_query += """
                FROM forum_comment c
                JOIN forum_useraccount u ON c.UserID_id = u.UserID
                """

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += """
                ORDER BY c.Timestamp DESC 
                LIMIT %s, %s;
                """
    params.extend([start_index, per_page])
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(base_query,params)

            results = cursor.fetchall()
            comments = [dict(zip(comment_username_col, row)) for row in results]
            comment_data = {"comments": comments}

        return utilities.response("SUCCESS", "Retrieved Post for pages", comment_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Get Comment by ID
def get_comment_by_id(comment_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ SELECT * FROM forum_comment WHERE CommentID = %s; """, 
                [comment_id],
            )

            result = cursor.fetchone()
            if result is None:
                return utilities.response("NOT_FOUND", "Post not found")

            comment = dict(zip(comment_col, result))
            comment_data = {"comment": comment}

        return utilities.response("SUCCESS", "Retrieved Comment by ID", comment_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Get Total Comment Count
def get_total_comment_count(userID=None):
    base_query = """ SELECT COUNT(*) FROM forum_comment """
    where_clauses = []
    params = []
    
    if userID:
        where_clauses.append("UserID_id = %s")
        params.append(userID)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    try:
        with connection.cursor() as cursor:
            cursor.execute(base_query, params)

            result = cursor.fetchone()
            total_comment_count = result[0] if result else 0
            comment_data = {"total_comment_count": total_comment_count}

        return utilities.response("SUCCESS", "Retrieved Total Post Count", comment_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Insert Comment
def insert_new_comment(commentContents, postID, userID):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO forum_comment (CommentContents, Timestamp, PostID_id, UserID_id)
                    VALUES (%s, %s, %s, %s);
                    """,
                    [commentContents, timestamp, postID, userID],
                )

        return utilities.response("SUCCESS", "Comment successfully created")

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Delete Comment by ID
def delete_comment_by_id(commentID):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """ DELETE FROM forum_comment WHERE CommentID = %s; """,
                    [commentID],
                )

        return utilities.response("SUCCESS", "Comment deleted successfully")
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Update Comment by ID
def update_comment_by_id(commentContents, commentID):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE forum_comment SET CommentContents = %s
                    WHERE CommentID = %s;
                    """,
                    [commentContents, commentID],
                )

        return utilities.response("SUCCESS", "Comment updated successfully")
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")