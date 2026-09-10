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
        cursor.execute(
            """
            INSERT INTO dompet (user_id, nama, jenis, is_utama)
            VALUES (%s, 'Cash', 'Cash', TRUE)
            """,
            (user_id,),
        )
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


def get_user_profile(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id, nama, email FROM users WHERE id = %s',
                (user_id,),
            )
            return cursor.fetchone()
    finally:
        conn.close()


def update_user_profile(user_id, nama, email, password=None):
    nama = (nama or '').strip()
    email = (email or '').strip().lower()
    if not nama or len(nama) > 100 or not email or len(email) > 100:
        return False, 'Nama dan email wajib diisi dengan benar.'
    if password is not None and len(password) < 6:
        return False, 'Password baru minimal 6 karakter.'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if password:
                cursor.execute(
                    """
                    UPDATE users
                    SET nama = %s, email = %s, password = %s
                    WHERE id = %s
                    """,
                    (nama, email, generate_password_hash(password), user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE users
                    SET nama = %s, email = %s
                    WHERE id = %s
                    """,
                    (nama, email, user_id),
                )
            updated = cursor.rowcount == 1
        conn.commit()
        return (True, 'Profil berhasil diperbarui.') if updated else (False, 'Profil tidak ditemukan.')
    except Exception as error:
        conn.rollback()
        print(f'Error update profil: {error}')
        return False, 'Email sudah digunakan atau profil gagal diperbarui.'
    finally:
        conn.close()