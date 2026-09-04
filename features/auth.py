from db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

def register_user(nama, email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_pw = generate_password_hash(password)
    
    try:
        cursor.execute(
            "INSERT INTO users (nama, email, password) VALUES (%s, %s, %s) RETURNING id",
            (nama, email, hashed_pw)
        )
        user_id = cursor.fetchone()['id']
        conn.commit()
        return True, user_id
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def check_user_login(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        return user
    return None