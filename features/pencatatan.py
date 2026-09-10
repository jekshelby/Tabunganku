from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import get_db_connection


def _parse_nominal(value):
    try:
        nominal = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None
    nominal = nominal.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return nominal if nominal > 0 else None

def get_kategori_transaksi():
    """Mengembalikan daftar kategori default untuk transaksi."""
    return {
        'pengeluaran': [
            'Makanan & Minuman',
            'Transportasi',
            'Belanja',
            'Tagihan & Utilitas',
            'Hiburan',
            'Kesehatan',
            'Lainnya'
        ],
        'pemasukan': [
            'Gaji',
            'Bonus',
            'Investasi',
            'Hadiah',
            'Lainnya'
        ]
    }

def simpan_transaksi_baru(user_id, tipe, nominal, kategori, catatan="", dompet_id=None):
    """Menyimpan data transaksi baru khusus milik user_id tertentu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        tipe = (tipe or '').strip().capitalize()
        if tipe not in {'Pemasukan', 'Pengeluaran'}:
            return False
        if not kategori or not str(kategori).strip():
            return False
        nominal = _parse_nominal(nominal)
        if not nominal:
            return False

        if dompet_id:
            cursor.execute('SELECT id FROM dompet WHERE id = %s AND user_id = %s', (dompet_id, user_id))
        else:
            cursor.execute('SELECT id FROM dompet WHERE user_id = %s AND is_utama = TRUE ORDER BY id LIMIT 1', (user_id,))
        dompet = cursor.fetchone()
        if not dompet:
            return False

        query = """
            INSERT INTO transaksi (user_id, tipe, nominal, kategori, catatan, dompet_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, tipe, nominal, kategori, catatan, dompet['id']))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error simpan transaksi: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_transaksi(user_id, transaksi_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tanggal, tipe, nominal, kategori, catatan, tabungan_id, dompet_id
                FROM transaksi
                WHERE id = %s AND user_id = %s
                """,
                (transaksi_id, user_id),
            )
            return cursor.fetchone()
    finally:
        conn.close()


def edit_transaksi(user_id, transaksi_id, tipe, nominal, kategori, catatan=''):
    tipe = (tipe or '').strip().capitalize()
    nominal = _parse_nominal(nominal)
    kategori = (kategori or '').strip()
    if tipe not in {'Pemasukan', 'Pengeluaran'} or not nominal or not kategori:
        return False

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT tabungan_id FROM transaksi WHERE id = %s AND user_id = %s',
                (transaksi_id, user_id),
            )
            existing = cursor.fetchone()
            if not existing or existing['tabungan_id'] is not None:
                return False
            cursor.execute(
                """
                UPDATE transaksi
                SET tipe = %s, nominal = %s, kategori = %s, catatan = %s
                WHERE id = %s AND user_id = %s
                """,
                (tipe, nominal, kategori, (catatan or '').strip() or None, transaksi_id, user_id),
            )
            updated = cursor.rowcount == 1
        conn.commit()
        return updated
    except Exception as error:
        conn.rollback()
        print(f'Error edit transaksi: {error}')
        return False
    finally:
        conn.close()


def hapus_transaksi(user_id, transaksi_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT tabungan_id FROM transaksi WHERE id = %s AND user_id = %s',
                (transaksi_id, user_id),
            )
            existing = cursor.fetchone()
            if not existing or existing['tabungan_id'] is not None:
                return False
            cursor.execute(
                'DELETE FROM transaksi WHERE id = %s AND user_id = %s',
                (transaksi_id, user_id),
            )
            deleted = cursor.rowcount == 1
        conn.commit()
        return deleted
    except Exception as error:
        conn.rollback()
        print(f'Error hapus transaksi: {error}')
        return False
    finally:
        conn.close()