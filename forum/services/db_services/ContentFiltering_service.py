from django.db import connection
from .. import utilities  # Assuming you're following same structure

filter_col = ["FilterID", "FilterContent"]

# MARK: Get All Filtered Words
def get_all_filtered_words():
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM forum_filtering;"""
            )
            results = cursor.fetchall()
            filters = [dict(zip(filter_col, row)) for row in results]
            return utilities.response("SUCCESS", "Filtered words retrieved successfully", filters)
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Add New Filtered Word
def insert_filtered_word(content):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO forum_filtering (FilterContent) VALUES (%s);""",
                [content.lower()],
            )
        return utilities.response("SUCCESS", "Filtered word added successfully")
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Delete Filtered Word
def delete_filtered_word_by_id(filter_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """DELETE FROM forum_filtering WHERE FilterID = %s;""",
                [filter_id],
            )
        return utilities.response("SUCCESS", "Filtered word deleted successfully")
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
