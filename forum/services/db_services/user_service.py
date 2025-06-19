import logging  # Add this import at the top of the file
import traceback
from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import authenticate
from .. import utilities

user_col = ["UserID", "Username", "Email",
            "Password", "Role", "EmailVerificationCode"]

# MARK: Login Authentication
def authenticate_user(email, password):
    try:

        user = authenticate(username=email, password=password)

        if user is None:
            return utilities.response("INVALID", "User login was unsuccessfully")


        with connection.cursor() as cursor:
            cursor.execute(
                """ SELECT * FROM forum_useraccount WHERE Email = %s; """,
                [email],
            )

            result = cursor.fetchone()

            if result is None:
                return utilities.response("NOT_FOUND", "User not found")
            

            user_data = dict(zip(user_col, result))

            # if not check_password(password, user_data["Password"]):
            #     return utilities.response("INVALID", "User login was unsuccessfully")

        return utilities.response("SUCCESS", "User login was successfully", user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


logger = logging.getLogger(__name__)

# MARK: User Registration


def insert_new_user(username, email, password, role, emailVerificationCode):
    try:
        hash_password = make_password(password)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO forum_useraccount (Username, Email, Password, Role, EmailVerificationCode)
                VALUES (%s, %s, %s, %s, %s);
                """,
                [username, email, hash_password, role, emailVerificationCode],
            )

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
                return utilities.response("NOT_FOUND", "User not found")

            user_data = dict(zip(user_col, result))

            return utilities.response("SUCCESS", "User was found", user_data)

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
                return utilities.response("NOT_FOUND", "User not found")

            user_data = dict(zip(user_col, result))

            return utilities.response("SUCCESS", "User was found", user_data)

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
                return utilities.response("NOT_FOUND", "User not found")

            user_data = dict(zip(user_col, result))

            return utilities.response("SUCCESS", "User was found", user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")

# MARK: Upate User Profile
def update_user_profile(user_id, username, email):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE forum_useraccount
                SET Username = %s, Email = %s
                WHERE UserID = %s;
                """,
                [username, email, user_id],
            )

        return utilities.response("SUCCESS", "User Profile updated successfully")
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")
    
# MARK: Upate User Password
def update_user_password(user_id, password):
    try:
        hash_password = make_password(password)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE forum_useraccount
                SET Password = %s WHERE UserID = %s;
                """,
                [hash_password, user_id],
            )

        return utilities.response("SUCCESS", "User Profile updated successfully")
    
    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")