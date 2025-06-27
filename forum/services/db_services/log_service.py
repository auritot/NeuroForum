from django.db import connection
from .. import utilities
from datetime import datetime

log_username_col = ["LogID", "Timestamp", "LogContent", "Category", "UserID_id"]

# MARK: Log Action
def log_action(logContent, performedBy):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ INSERT INTO forum_logs (Timestamp, LogContent, PerformedBy) VALUES (%s, %s, %s); """,
                [timestamp, logContent, performedBy],
            )

        return utilities.response("SUCCESS", "Log successfullly recorded")

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Get Total Log Count
def get_total_log_count():
    try:
        with connection.cursor() as cursor:
            cursor.execute(""" SELECT COUNT(*) FROM forum_logs """)

            result = cursor.fetchone()
            total_log_count = result[0] if result else 0
            log_data = {"total_log_count": total_log_count}

        return utilities.response("SUCCESS", "Retrieved Total Log Count", log_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Get Logs for page
def get_logs_for_page(start_index, per_page):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT l.*, u.Username FROM forum_logs l
                JOIN forum_useraccount u ON l.PerformedBy = u.UserID
                ORDER BY l.Timestamp DESC LIMIT %s, %s;
                """, 
                [start_index, per_page]
            )

            results = cursor.fetchall()
            logs = [dict(zip(log_username_col, row)) for row in results]
            log_data = {"logs": logs}

        return utilities.response("SUCCESS", f"Retrieved Posts for the page {start_index}", log_data)
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")