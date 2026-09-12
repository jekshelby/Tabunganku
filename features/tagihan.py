from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import get_db_connection
from features.dompet import hitung_saldo_dompet


def _parse_nominal(value):
    try:
        nominal = Decimal(str(value).strip()).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, AttributeError):
        return None
    return nominal if nominal > 0 else None


def get_semua_tagihan(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nama, kategori, nominal, jatuh_tempo, status, catatan, dompet_id, created_at
                FROM tagihan
                WHERE user_id = %s
                ORDER BY CASE WHEN status = 'belum_lunas' THEN 0 ELSE 1 END, jatuh_tempo NULLS LAST, created_at DESC
                """,
                (user_id,),
            )
            return cursor.fetchall()
    finally:
        conn.close()


def buat_tagihan(user_id, nama, nominal, jatuh_tempo=None, kategori='Lainnya', catatan=''):
    nominal = _parse_nominal(nominal)
    nama = (nama or '').strip()
    if not nama or not nominal:
        return False, 'Nama dan nominal tagihan wajib diisi.'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tagihan (user_id, nama, kategori, nominal, jatuh_tempo, catatan)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (user_id, nama, (kategori or 'Lainnya').strip(), nominal, jatuh_tempo or None, (catatan or '').strip() or None),
            )
            tagihan_id = cursor.fetchone()['id']
        conn.commit()
        return True, tagihan_id
    except Exception as error:
        conn.rollback()
        print(f'Error buat tagihan: {error}')
        return False, 'Tagihan gagal dibuat.'
    finally:
        conn.close()


def bayar_tagihan(user_id, tagihan_id, dompet_id):
    try:
        selected_dompet_id = int(dompet_id)
    except (TypeError, ValueError):
        return False, 'Dompet tidak ditemukan.'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nama, kategori, nominal, status FROM tagihan WHERE id = %s AND user_id = %s FOR UPDATE",
                (tagihan_id, user_id),
            )
            tagihan = cursor.fetchone()
            if not tagihan:
                return False, 'Tagihan tidak ditemukan.'
            if tagihan['status'] == 'lunas':
                return False, 'Tagihan ini sudah lunas.'
            cursor.execute(
                'SELECT id FROM dompet WHERE id = %s AND user_id = %s FOR UPDATE',
                (selected_dompet_id, user_id),
            )
            dompet = cursor.fetchone()
            if not dompet:
                return False, 'Dompet tidak ditemukan.'
            if hitung_saldo_dompet(cursor, user_id, dompet['id']) < tagihan['nominal']:
                return False, 'Saldo dompet tidak mencukupi untuk membayar tagihan.'
            cursor.execute(
                """
                INSERT INTO transaksi (user_id, tipe, nominal, kategori, catatan, dompet_id)
                VALUES (%s, 'Pengeluaran', %s, %s, %s, %s)
                """,
                (user_id, tagihan['nominal'], f"Tagihan - {tagihan['nama']}"[:50], 'Pembayaran tagihan', selected_dompet_id),
            )
            cursor.execute(
                "UPDATE tagihan SET status = 'lunas', paid_at = CURRENT_TIMESTAMP, dompet_id = %s WHERE id = %s AND user_id = %s",
                (selected_dompet_id, tagihan_id, user_id),
            )
        conn.commit()
        return True, 'Tagihan berhasil dibayar dan dicatat sebagai pengeluaran.'
    except Exception as error:
        conn.rollback()
        print(f'Error bayar tagihan: {error}')
        return False, 'Tagihan gagal dibayar.'
    finally:
        conn.close()


def hapus_tagihan(user_id, tagihan_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM tagihan WHERE id = %s AND user_id = %s', (tagihan_id, user_id))
            deleted = cursor.rowcount == 1
        conn.commit()
        return deleted, 'Tagihan berhasil dihapus.' if deleted else 'Tagihan tidak ditemukan.'
    except Exception as error:
        conn.rollback()
        return False, 'Tagihan gagal dihapus.'
    finally:
        conn.close()
