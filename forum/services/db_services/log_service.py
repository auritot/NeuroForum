from django.db import connection
from .. import utilities
from datetime import datetime

log_username_col = ["LogID", "Timestamp", "LogContent", "Category", "UserID_id"]

# MARK: Log Action
def log_action(logContent, user_id, isSystem=False, isError=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    category = f'{"System" if isSystem else "User"} {"Error" if isError else "Action"}'

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ INSERT INTO forum_logs (Timestamp, LogContent, Category, UserID_id) VALUES (%s, %s, %s, %s); """,
                [timestamp, logContent, category, user_id],
            )

        return utilities.response("SUCCESS", "Log successfullly recorded")

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Get Total Log Count
def get_total_log_count(search, category):
    base_query = """ SELECT COUNT(*) FROM forum_logs """
    where_clauses = []
    params = []

    if search:
        where_clauses.append("UserID_id = %s")
        params.append(search)

    if category:
        where_clauses.append("Category = %s")
        params.append(category)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    try:
        with connection.cursor() as cursor:
            cursor.execute(base_query, params)

            result = cursor.fetchone()
            total_log_count = result[0] if result else 0
            log_data = {"total_log_count": total_log_count}

        return utilities.response("SUCCESS", "Retrieved Total Log Count", log_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Get Logs for page
def get_logs_for_page(start_index, per_page, sort_by, search, category):
    timestamp_order = "DESC" if sort_by == "newest" else "ASC"

    base_query = """ SELECT * FROM forum_logs """
    where_clauses = []
    params = []

    if search:
        where_clauses.append("UserID_id = %s")
        params.append(search)

    if category:
        where_clauses.append("Category = %s")
        params.append(category)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += f"""
                ORDER BY Timestamp {timestamp_order}
                LIMIT %s, %s;
                """

    params.extend([start_index, per_page])

    try:
        with connection.cursor() as cursor:
            cursor.execute(base_query, params)

            results = cursor.fetchall()
            logs = [dict(zip(log_username_col, row)) for row in results]
            log_data = {"logs": logs}

        return utilities.response("SUCCESS", f"Retrieved Posts for the page {start_index}", log_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")