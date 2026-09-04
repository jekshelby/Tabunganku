from db import get_db_connection

def get_ringkasan_keuangan(user_id):
    """Mengambil total saldo, pemasukan, pengeluaran, dan 5 transaksi terakhir milik user_id."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Total Pemasukan
        cursor.execute("""
            SELECT COALESCE(SUM(nominal), 0) as total 
            FROM transaksi 
            WHERE user_id = %s AND tipe = 'Pemasukan'
        """, (user_id,))
        total_pemasukan = float(cursor.fetchone()['total'])

        # Total Pengeluaran
        cursor.execute("""
            SELECT COALESCE(SUM(nominal), 0) as total 
            FROM transaksi 
            WHERE user_id = %s AND tipe = 'Pengeluaran'
        """, (user_id,))
        total_pengeluaran = float(cursor.fetchone()['total'])

        # Hitung Saldo Utuh
        total_saldo = total_pemasukan - total_pengeluaran

        # 5 Transaksi Terakhir
        cursor.execute("""
            SELECT id, tanggal, tipe, nominal, kategori, catatan, created_at
            FROM transaksi 
            WHERE user_id = %s 
            ORDER BY tanggal DESC, created_at DESC 
            LIMIT 5
        """, (user_id,))
        transaksi_terakhir = cursor.fetchall()

        return {
            'total_saldo': total_saldo,
            'sisa_saldo': total_saldo,  # Alias agar Jinja2 tidak menganggap Undefined
            'total_pemasukan': total_pemasukan,
            'total_pengeluaran': total_pengeluaran,
            'transaksi_terakhir': transaksi_terakhir
        }
    except Exception as e:
        print(f"Error get_ringkasan_keuangan: {e}")
        return {
            'total_saldo': 0,
            'sisa_saldo': 0,
            'total_pemasukan': 0,
            'total_pengeluaran': 0,
            'transaksi_terakhir': []
        }
    finally:
        cursor.close()
        conn.close()


def get_semua_riwayat(user_id):
    """Mengambil seluruh riwayat transaksi milik user_id tertentu."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, tanggal, tipe, nominal, kategori, catatan, created_at
            FROM transaksi 
            WHERE user_id = %s 
            ORDER BY tanggal DESC, created_at DESC
        """, (user_id,))
        riwayat = cursor.fetchall()
        return riwayat
    except Exception as e:
        print(f"Error get_semua_riwayat: {e}")
        return []
    finally:
        cursor.close()
        conn.close()