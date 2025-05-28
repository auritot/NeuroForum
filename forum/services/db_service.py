from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
from . import utilities


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
                return utilities.response("NOT_FOUND", "User not found")

            user_data = {
                "UserID": result[0],
                "Username": result[1],
                "Email": result[2],
                "Password": result[3],
                "Role": result[4],
            }

            if not check_password(password, user_data["Password"]):
                return utilities.response("INVALID", "User login was unsuccessfully")

        return utilities.response("SUCCESS", "User login was successfully", user_data)

    except Exception as e:
        return utilities.response("ERROR", f"An unexpected error occurred: {e}")


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
        return utilities.response("FAILURE", f"An unexpected error occurred: {e}")
