from django.db import connection
from django.contrib.auth.hashers import check_password, make_password


# MARK: Login Authentication
def authenticate_user(email, password):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """ SELECT * FROM forum_useraccount WHERE Email = %s; """,
                [email],
            )

            row = cursor.fetchone()
            if row is None:
                return {"status": "NOTFOUND", "message": "User not found"}
            if check_password(password, row[3]):
                return {"status": "INVALID", "message": "User login was unsuccessfully"}

        return {"status": "SUCCESS", "message": "User login was successfully"}
    except Exception as e:
        return {"status": "FAILURE", "message": f"An unexpected error occurred: {e}"}


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

        return {"status": "SUCCESS", "message": "User account successfully created"}
    except Exception as e:
        return {"status": "FAILURE", "message": f"An unexpected error occurred: {e}"}
