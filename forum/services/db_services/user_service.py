import logging  # Add this import at the top of the file
import traceback
from django.db import connection, transaction
from django.contrib.auth.hashers import check_password, make_password
from .. import utilities
from . import log_service

user_col = ["UserID", "Username", "Email",
            "Password", "Role"]

USER_FOUND_MSG = "User was found"
USER_NOT_FOUND_MSG = "User not found"

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
                return utilities.response("NOT_FOUND", USER_NOT_FOUND_MSG)

            user_data = dict(zip(user_col, result))

            if not check_password(password, user_data["Password"]):
                return utilities.response("INVALID", "User login was unsuccessfully")

        return utilities.response("SUCCESS", "User login was successfully", user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


logger = logging.getLogger(__name__)

# MARK: User Registration


def insert_new_user(username, email, password, role):
    hash_password = make_password(password)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO forum_useraccount (Username, Email, Password, Role)
                    VALUES (%s, %s, %s, %s);
                    """,
                    [username, email, hash_password, role],
                )

                cursor.execute("SELECT LAST_INSERT_ID();")
                user_id = cursor.fetchone()[0]

                log_service.log_action("New account have been registered", user_id)

        return utilities.response("SUCCESS", "User account successfully created")

    except Exception as e:
        # --- IMPORTANT TEMPORARY DEBUGGING LINES ---
        logger.error(f"Error inserting new user: {e}")
        # Prints the full traceback to logs
        logger.error(traceback.format_exc())
        # --- END TEMPORARY DEBUGGING LINES ---
        
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Get User by Email


def get_user_by_email(email):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ SELECT * FROM forum_useraccount WHERE Email = %s; """,
                [email],
            )

            result = cursor.fetchone()
            if result is None:
                return utilities.response("NOT_FOUND", USER_NOT_FOUND_MSG)

            user_data = dict(zip(user_col, result))

            return utilities.response("SUCCESS", USER_FOUND_MSG, user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Get User by Username


def get_user_by_username(username):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ SELECT * FROM forum_useraccount WHERE Username = %s; """,
                [username],
            )

            result = cursor.fetchone()
            if result is None:
                return utilities.response("NOT_FOUND", USER_NOT_FOUND_MSG)

            user_data = dict(zip(user_col, result))

            return utilities.response("SUCCESS", USER_FOUND_MSG, user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Get User by ID


def get_user_by_id(user_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ SELECT * FROM forum_useraccount WHERE UserID = %s; """,
                [user_id],
            )

            result = cursor.fetchone()
            if result is None:
                return utilities.response("NOT_FOUND", USER_NOT_FOUND_MSG)

            user_data = dict(zip(user_col, result))

            return utilities.response("SUCCESS", USER_FOUND_MSG, user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Upate User Profile


def update_user_profile(user_id, username, email):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE forum_useraccount SET Username = %s, Email = %s
                    WHERE UserID = %s;
                    """,
                    [username, email, user_id],
                )

                log_service.log_action("User profile have been updated", user_id)

        return utilities.response("SUCCESS", "User Profile updated successfully")

    except Exception as e:
        log_service.log_action(f"Failed to update user: {e}", user_id, isSystem=True, isError=True)
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Upate User Password


def update_user_password(user_id, password):
    hash_password = make_password(password)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """ UPDATE forum_useraccount SET Password = %s WHERE UserID = %s; """,
                    [hash_password, user_id],
                )

                log_service.log_action("User profile have been updated", user_id)

        return utilities.response("SUCCESS", "User Password updated successfully")

    except Exception as e:
        log_service.log_action(f"Failed to update user: {e}", user_id, isSystem=True, isError=True)
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Update User Role


def update_user_role(user_id, role, performed_by):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Fetch username first
                cursor.execute(
                    "SELECT Username FROM forum_useraccount WHERE UserID = %s;",
                    [user_id]
                )
                result = cursor.fetchone()
                if not result:
                    return utilities.response("ERROR", USER_NOT_FOUND_MSG)

                username = result[0]

                # Perform role update
                cursor.execute(
                    "UPDATE forum_useraccount SET Role = %s WHERE UserID = %s;",
                    [role, user_id]
                )

                log_service.log_action(
                    f"Updated user role to {role} for: {username}", performed_by)

        return utilities.response("SUCCESS", f"{username}'s role successfully updated to {role}")

    except Exception as e:
        log_service.log_action(f"Failed to update user: {e}", user_id, isSystem=True, isError=True)
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Delete User by ID


def delete_user_by_id(user_id, performed_by):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # First, get the username before deletion
                cursor.execute(
                    """ SELECT Username FROM forum_useraccount WHERE UserID = %s; """,
                    [user_id],
                )
                result = cursor.fetchone()
                if not result:
                    return utilities.response("ERROR", USER_NOT_FOUND_MSG)
                username = result[0]

                # Then, delete the user
                cursor.execute(
                    """ DELETE FROM forum_useraccount WHERE UserID = %s; """,
                    [user_id],
                )

                log_service.log_action(
                    f"Deleted user account: {username} (ID: {user_id})", performed_by)

        return utilities.response("SUCCESS", f"User '{username}' deleted successfully")

    except Exception as e:
        log_service.log_action(f"Failed to delete user: {e}", user_id, isSystem=True, isError=True)
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
