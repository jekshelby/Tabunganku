from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import get_db_connection
from features.dompet import hitung_saldo_dompet


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

def simpan_transaksi_baru(user_id, tipe, nominal, kategori, catatan="", dompet_id=None, dompet_tujuan_id=None):
    """Menyimpan data transaksi baru khusus milik user_id tertentu."""
    tipe = (tipe or '').strip().capitalize()
    if tipe == 'Alokasi dana':
        return alokasikan_dana(user_id, nominal, dompet_id, dompet_tujuan_id, catatan)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
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


def _transaksi_terkunci(row):
    if not row:
        return True
    if row.get('tabungan_id') is not None:
        return True
    if row.get('dompet_tujuan_id') is not None:
        return True
    return (row.get('tipe') or '').strip().lower() == 'alokasi dana'


def alokasikan_dana(user_id, nominal, dompet_sumber_id, dompet_tujuan_id, catatan=''):
    nominal = _parse_nominal(nominal)
    if not nominal or not dompet_sumber_id or not dompet_tujuan_id or str(dompet_sumber_id) == str(dompet_tujuan_id):
        return False

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM dompet
                WHERE id IN (%s, %s) AND user_id = %s
                ORDER BY id
                FOR UPDATE
                """,
                (dompet_sumber_id, dompet_tujuan_id, user_id),
            )
            locked = {int(row['id']) for row in cursor.fetchall()}
            try:
                sumber_id = int(dompet_sumber_id)
                tujuan_id = int(dompet_tujuan_id)
            except (TypeError, ValueError):
                return False
            if sumber_id not in locked or tujuan_id not in locked:
                return False

            saldo_sumber = hitung_saldo_dompet(cursor, user_id, sumber_id)
            if saldo_sumber < nominal:
                return False

            cursor.execute(
                """
                INSERT INTO transaksi (user_id, tipe, nominal, kategori, catatan, dompet_id, dompet_tujuan_id)
                VALUES (%s, 'Alokasi Dana', %s, 'Alokasi Dana', %s, %s, %s)
                """,
                (user_id, nominal, (catatan or '').strip() or 'Pemindahan dana antar dompet', sumber_id, tujuan_id),
            )
        conn.commit()
        return True
    except Exception as error:
        conn.rollback()
        print(f'Error alokasi dana: {error}')
        return False
    finally:
        conn.close()


def get_transaksi(user_id, transaksi_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tanggal, tipe, nominal, kategori, catatan, tabungan_id, dompet_id, dompet_tujuan_id
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
                """
                SELECT tabungan_id, dompet_tujuan_id, tipe
                FROM transaksi
                WHERE id = %s AND user_id = %s
                """,
                (transaksi_id, user_id),
            )
            existing = cursor.fetchone()
            if _transaksi_terkunci(existing):
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
                """
                SELECT tabungan_id, dompet_tujuan_id, tipe
                FROM transaksi
                WHERE id = %s AND user_id = %s
                """,
                (transaksi_id, user_id),
            )
            existing = cursor.fetchone()
            if _transaksi_terkunci(existing):
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