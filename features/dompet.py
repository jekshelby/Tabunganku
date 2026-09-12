from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import get_db_connection


def _parse_nominal(value):
    try:
        nominal = Decimal(str(value).strip()).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, AttributeError):
        return None
    return nominal if nominal > 0 else None


SALDO_DOMPET_SQL = """
COALESCE(SUM(CASE
    WHEN LOWER(t.tipe) = 'pemasukan' THEN t.nominal
    WHEN LOWER(t.tipe) = 'pengeluaran' THEN -t.nominal
    WHEN LOWER(t.tipe) = 'alokasi dana' AND t.dompet_id = d.id THEN -t.nominal
    WHEN LOWER(t.tipe) = 'alokasi dana' AND t.dompet_tujuan_id = d.id THEN t.nominal
    ELSE 0
END), 0)
"""


def hitung_saldo_dompet(cursor, user_id, dompet_id):
    cursor.execute(
        """
        SELECT COALESCE(SUM(CASE
            WHEN LOWER(tipe) = 'pemasukan' THEN nominal
            WHEN LOWER(tipe) = 'pengeluaran' THEN -nominal
            WHEN LOWER(tipe) = 'alokasi dana' AND dompet_id = %s THEN -nominal
            WHEN LOWER(tipe) = 'alokasi dana' AND dompet_tujuan_id = %s THEN nominal
            ELSE 0
        END), 0) AS saldo
        FROM transaksi
        WHERE user_id = %s AND (dompet_id = %s OR dompet_tujuan_id = %s)
        """,
        (dompet_id, dompet_id, user_id, dompet_id, dompet_id),
    )
    row = cursor.fetchone()
    return row['saldo'] if row else Decimal('0')


def get_semua_dompet(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT d.id, d.nama, d.jenis, d.warna, d.is_utama, d.created_at,
                    {SALDO_DOMPET_SQL} AS saldo
                FROM dompet d
                LEFT JOIN transaksi t
                    ON t.user_id = d.user_id
                   AND (t.dompet_id = d.id OR t.dompet_tujuan_id = d.id)
                WHERE d.user_id = %s
                GROUP BY d.id
                ORDER BY d.is_utama DESC, d.created_at ASC
                """,
                (user_id,),
            )
            return cursor.fetchall()
    finally:
        conn.close()


def buat_dompet(user_id, nama, jenis='E-wallet', warna='#1c1c1e'):
    nama = (nama or '').strip()
    jenis = (jenis or 'Lainnya').strip()
    if not nama or len(nama) > 80:
        return False, 'Nama dompet wajib diisi.'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO dompet (user_id, nama, jenis, warna) VALUES (%s, %s, %s, %s) RETURNING id",
                (user_id, nama, jenis, warna or '#1c1c1e'),
            )
            dompet_id = cursor.fetchone()['id']
        conn.commit()
        return True, dompet_id
    except Exception as error:
        conn.rollback()
        print(f'Error buat dompet: {error}')
        return False, 'Dompet gagal dibuat.'
    finally:
        conn.close()


def hapus_dompet(user_id, dompet_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT is_utama FROM dompet WHERE id = %s AND user_id = %s', (dompet_id, user_id))
            dompet = cursor.fetchone()
            if not dompet:
                return False, 'Dompet tidak ditemukan.'
            if dompet['is_utama']:
                return False, 'Dompet Utama tidak dapat dihapus.'
            cursor.execute(
                """
                SELECT COUNT(*) AS jumlah
                FROM transaksi
                WHERE user_id = %s AND (dompet_id = %s OR dompet_tujuan_id = %s)
                """,
                (user_id, dompet_id, dompet_id),
            )
            if cursor.fetchone()['jumlah']:
                return False, 'Dompet yang sudah memiliki transaksi tidak dapat dihapus.'
            cursor.execute('DELETE FROM dompet WHERE id = %s AND user_id = %s', (dompet_id, user_id))
        conn.commit()
        return True, 'Dompet berhasil dihapus.'
    except Exception as error:
        conn.rollback()
        print(f'Error hapus dompet: {error}')
        return False, 'Dompet gagal dihapus.'
    finally:
        conn.close()


def get_dompet_options(user_id):
    return get_semua_dompet(user_id)
