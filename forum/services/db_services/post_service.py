from django.db import connection, transaction
from django.contrib.auth.hashers import check_password, make_password
from .. import utilities
from datetime import datetime
from . import log_service

post_username_comment_count_col = ["PostID", "Title", "PostContent", "Timestamp", "CommentStatus", "UserID_id", "Username", "CommentCount"]

# MARK: Get Total Post Count
def get_total_post_count(userID=None):
    base_query = """ SELECT COUNT(*) FROM forum_post """
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
            total_post_count = result[0] if result else 0
            post_data = {"total_post_count": total_post_count}

        return utilities.response("SUCCESS", "Retrieved Total Post Count", post_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Get Posts for page
def get_posts_for_page(start_index, per_page, userID=None):
    base_query = """
                SELECT p.*, u.Username, COUNT(c.CommentID) AS CommentCount
                FROM forum_post p
                JOIN forum_useraccount u ON p.UserID_id = u.UserID
                LEFT JOIN forum_comment c ON c.PostID_id = p.PostID
                """
    where_clauses = []
    params = []

    if userID:
        where_clauses.append("p.UserID_id = %s")
        params.append(userID)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += """
                GROUP BY p.PostID, u.UserID
                ORDER BY p.Timestamp DESC
                LIMIT %s, %s;
                """
    params.extend([start_index, per_page])

    try:
        with connection.cursor() as cursor:
            cursor.execute(base_query, params)

            results = cursor.fetchall()
            posts = [dict(zip(post_username_comment_count_col, row)) for row in results]
            post_data = {"posts": posts}

        return utilities.response("SUCCESS", f"Retrieved Posts for the page {start_index}", post_data)
    
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

        return utilities.response("SUCCESS", "Retrieved Post by ID", post_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Insert Post
def insert_new_post(postTitle, postDescription, allowComments, userID):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    commentStatus = 1 if allowComments else 0

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO forum_post (Title, PostContent, Timestamp, CommentStatus, UserID_id)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    [postTitle, postDescription, timestamp, commentStatus, userID],
                )

                cursor.execute("SELECT LAST_INSERT_ID();")
                post_id = cursor.fetchone()[0]

                log_service.log_action("User posted a new post", userID)

        return utilities.response("SUCCESS", "Post created successfully", {"post_id": post_id})

    except Exception as e:
        log_service.log_action(f"Failed to create Post: {e}", userID, isSystem=True, isError=True)
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Update Post by ID
def update_post_by_id(postTitle, postDescription, allowComments, postID, userID):
    commentStatus = 1 if allowComments else 0

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """ 
                    UPDATE forum_post SET Title = %s, PostContent = %s, CommentStatus = %s 
                    WHERE PostID = %s;
                    """,
                    [postTitle, postDescription, commentStatus, postID],
                )

                log_service.log_action(f"User updated Post {postID}", userID)

        return utilities.response("SUCCESS", "Post updated successfully")
    
    except Exception as e:
        log_service.log_action(f"Failed to update Post {postID}", userID, isSystem=True, isError=True)
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Delete Post by ID
def delete_post_by_id(postID, userID, isAdmin=False):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """ DELETE FROM forum_comment WHERE PostID_id = %s; """,
                    [postID],
                )
                cursor.execute(
                    """ DELETE FROM forum_post WHERE PostID = %s; """,
                    [postID],
                )

                log_msg = f'{"Admin" if isAdmin else "User"} deleted Post {postID} and its comments'
                log_service.log_action(log_msg, userID)

        return utilities.response("SUCCESS", "The Post and its Comments deleted successfully")
    
    except Exception as e:
        log_service.log_action(f"Failed to delete Post {postID}: {e}", userID, isSystem=True, isError=True)
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Search Posts by Keyword
def search_posts_by_keyword(keyword, start_index=0, per_page=10, userID=None, sort_order="newest"):
    try:
        search_term = f"%{keyword}%"

        base_query = """
            SELECT p.*, u.Username, COUNT(c.CommentID) AS CommentCount
            FROM forum_post p
            JOIN forum_useraccount u ON p.UserID_id = u.UserID
            LEFT JOIN forum_comment c ON c.PostID_id = p.PostID
            WHERE (p.Title LIKE %s OR p.PostContent LIKE %s)
        """
        params = [search_term, search_term]

        if userID:
            base_query += " AND p.UserID_id = %s"
            params.append(userID)

        # Add sorting
        if sort_order == "oldest":
            order_clause = "ORDER BY p.Timestamp ASC"
        else:  # Default to newest
            order_clause = "ORDER BY p.Timestamp DESC"
        
        base_query += f"""
            GROUP BY p.PostID, u.UserID
            {order_clause}
            LIMIT %s, %s;
        """
        params.extend([start_index, per_page])

        with connection.cursor() as cursor:
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            posts = [dict(zip(post_username_comment_count_col, row)) for row in results]
            post_data = {"posts": posts}

        return utilities.response("SUCCESS", "Search results retrieved", post_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    

def get_search_post_count(keyword):
    try:
        search_term = f"%{keyword}%"
        query = """
            SELECT COUNT(*) 
            FROM forum_post p
            WHERE (p.Title LIKE %s OR p.PostContent LIKE %s)
        """
        params = [search_term, search_term]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            count = result[0] if result else 0

        return utilities.response("SUCCESS", "Search count retrieved", {"count": count})
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")