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
        # Check for duplicate
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT FilterID FROM forum_filtering WHERE FilterContent = %s;""",
                [content.lower()],
            )
            if cursor.fetchone():
                return utilities.response("ERROR", "Filtered word already exists")
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

# MARK: Update Filtered Word
def update_filtered_word_by_id(filter_id, content):
    try:
        # Check for duplicate in other records
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT FilterID FROM forum_filtering WHERE FilterContent = %s AND FilterID != %s;""",
                [content.lower(), filter_id],
            )
            if cursor.fetchone():
                return utilities.response("ERROR", "Another filtered word with this content already exists")
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE forum_filtering SET FilterContent = %s WHERE FilterID = %s;""",
                [content.lower(), filter_id],
            )
        return utilities.response("SUCCESS", "Filtered word updated successfully")
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


# MARK: Get All Filtered Words (Paginated)
def get_filtered_words_paginated(start_index, per_page, search_term=None, sort_by='FilterContent', sort_order='ASC'):
    try:
        with connection.cursor() as cursor:
            query = """SELECT FilterID, FilterContent FROM forum_filtering """
            params = []

            if search_term:
                query += " WHERE LOWER(FilterContent) LIKE %s "
                params.append(f"%{search_term.lower()}%") # Simple contains search
            
            # Ensure sort_by is a valid column to prevent SQL injection
            valid_sort_columns = ['FilterID', 'FilterContent']
            if sort_by not in valid_sort_columns:
                sort_by = 'FilterContent' # Default sort column
            
            # Ensure sort_order is either ASC or DESC
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'ASC'

            query += f" ORDER BY {sort_by} {sort_order.upper()} LIMIT %s OFFSET %s;"
            params.extend([per_page, start_index])
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            filters = [dict(zip(filter_col, row)) for row in results]
            return utilities.response("SUCCESS", "Filtered words retrieved successfully", filters)
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Get Total Filtered Words Count
def get_total_filtered_words_count(search_term=None):
    try:
        with connection.cursor() as cursor:
            query = """SELECT COUNT(FilterID) FROM forum_filtering"""
            params = []
            if search_term:
                query += " WHERE LOWER(FilterContent) LIKE %s"
                params.append(f"%{search_term.lower()}%") # Simple contains search
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            count = result[0] if result else 0
            return utilities.response("SUCCESS", "Total filtered words count retrieved successfully", {"total_filtered_words_count": count})
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Delete Multiple Filtered Words by IDs
def delete_filtered_words_by_ids(filter_ids):
    if not filter_ids:
        return utilities.response("ERROR", "No filter IDs provided for deletion.")
    try:
        with connection.cursor() as cursor:
            # Ensure filter_ids are integers to prevent SQL injection, though placeholders help
            safe_filter_ids = [int(fid) for fid in filter_ids]
            placeholders = ','.join(['%s'] * len(safe_filter_ids))
            query = f"DELETE FROM forum_filtering WHERE FilterID IN ({placeholders});"
            cursor.execute(query, safe_filter_ids)
            # Check if any rows were actually deleted
            if cursor.rowcount > 0:
                return utilities.response("SUCCESS", f"{cursor.rowcount} filtered word(s) deleted successfully.")
            else:
                return utilities.response("NOT_FOUND", "No matching filtered words found for deletion.")
    except ValueError:
        return utilities.response("ERROR", "Invalid filter ID format provided.")
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred during bulk deletion: {e}")

# MARK: Add Multiple New Filtered Words
def insert_multiple_filtered_words(words_list):
    if not words_list:
        return utilities.response("ERROR", "No words provided to add.")

    added_count = 0
    skipped_words = [] # To store words that were skipped (duplicates, empty, etc.)
    successfully_added_words = []

    try:
        with connection.cursor() as cursor:
            for word_content in words_list:
                content = str(word_content).strip().lower() # Ensure string, strip whitespace, and lowercase
                if not content:
                    skipped_words.append({"word": word_content, "reason": "Empty or whitespace only"})
                    continue

                # Check for duplicate
                cursor.execute(
                    """SELECT FilterID FROM forum_filtering WHERE FilterContent = %s;""",
                    [content],
                )
                if cursor.fetchone():
                    skipped_words.append({"word": word_content, "reason": "Duplicate"})
                    continue
                
                # Insert the new word
                cursor.execute(
                    """INSERT INTO forum_filtering (FilterContent) VALUES (%s);""",
                    [content],
                )
                added_count += 1
                successfully_added_words.append(content)
        
        message = f"{added_count} word(s) added successfully."
        if skipped_words:
            message += f" {len(skipped_words)} word(s) were skipped."
        
        return utilities.response(
            "SUCCESS" if added_count > 0 else "INFO", 
            message, 
            {"added_count": added_count, "skipped_words": skipped_words, "successfully_added_words": successfully_added_words}
        )
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred during bulk insert: {e}")

# MARK: Get Filtered Word by ID
def get_filtered_word_by_id(filter_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM forum_filtering WHERE FilterID = %s;""",
                [filter_id],
            )
            result = cursor.fetchone()
            if result:
                filter_word = dict(zip(filter_col, result))
                return utilities.response("SUCCESS", "Filtered word retrieved successfully", filter_word)
            else:
                return utilities.response("NOT_FOUND", "Filtered word not found")
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
