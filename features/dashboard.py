from db import get_db_connection
from features.dompet import get_semua_dompet

def get_ringkasan_keuangan(user_id):
    """Mengambil total saldo, pemasukan, pengeluaran, dan 5 transaksi terakhir milik user_id."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        dompet = get_semua_dompet(user_id)

        # Total Pemasukan
        cursor.execute("""
            SELECT COALESCE(SUM(nominal), 0) as total 
            FROM transaksi t
            WHERE t.user_id = %s AND LOWER(t.tipe) = 'pemasukan'
        """, (user_id,))
        total_pemasukan = float(cursor.fetchone()['total'])

        # Total Pengeluaran
        cursor.execute("""
            SELECT COALESCE(SUM(nominal), 0) as total 
            FROM transaksi t
            WHERE t.user_id = %s AND LOWER(t.tipe) = 'pengeluaran'
        """, (user_id,))
        total_pengeluaran = float(cursor.fetchone()['total'])

        # Total saldo adalah penjumlahan seluruh saldo dompet.
        total_saldo = sum(float(wallet['saldo']) for wallet in dompet)

        # 5 Transaksi Terakhir
        cursor.execute("""
            SELECT t.id, t.tanggal, LOWER(t.tipe) AS tipe, t.nominal, t.kategori, t.catatan, t.tabungan_id, t.dompet_id, t.dompet_tujuan_id, d.nama AS dompet_nama, tujuan.nama AS dompet_tujuan_nama, t.created_at
            FROM transaksi t
            LEFT JOIN dompet d ON d.id = t.dompet_id
            LEFT JOIN dompet tujuan ON tujuan.id = t.dompet_tujuan_id
            WHERE t.user_id = %s
            ORDER BY t.tanggal DESC, t.created_at DESC
            LIMIT 5
        """, (user_id,))
        transaksi_terakhir = cursor.fetchall()

        return {
            'total_saldo': total_saldo,
            'sisa_saldo': total_saldo,  # Alias agar Jinja2 tidak menganggap Undefined
            'total_pemasukan': total_pemasukan,
            'total_pengeluaran': total_pengeluaran,
            'transaksi_terakhir': transaksi_terakhir
            , 'dompet': dompet
        }
    except Exception as e:
        print(f"Error get_ringkasan_keuangan: {e}")
        return {
            'total_saldo': 0,
            'sisa_saldo': 0,
            'total_pemasukan': 0,
            'total_pengeluaran': 0,
            'transaksi_terakhir': []
            , 'dompet': []
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
            SELECT t.id, t.tanggal, LOWER(t.tipe) AS tipe, t.nominal, t.kategori, t.catatan, t.tabungan_id, t.dompet_id, t.dompet_tujuan_id, d.nama AS dompet_nama, tujuan.nama AS dompet_tujuan_nama, t.created_at
            FROM transaksi t
            LEFT JOIN dompet d ON d.id = t.dompet_id
            LEFT JOIN dompet tujuan ON tujuan.id = t.dompet_tujuan_id
            WHERE t.user_id = %s
            ORDER BY t.tanggal DESC, t.created_at DESC
        """, (user_id,))
        transaksi = cursor.fetchall()
        riwayat = {}

        for item in transaksi:
            tanggal = item['tanggal'].isoformat()
            group = riwayat.setdefault(tanggal, {
                'items': [],
                'total_pemasukan': 0,
                'total_pengeluaran': 0,
            })
            group['items'].append(item)
            if item['tipe'] == 'pemasukan':
                group['total_pemasukan'] += item['nominal']
            elif item['tipe'] == 'pengeluaran':
                group['total_pengeluaran'] += item['nominal']

        return riwayat
    except Exception as e:
        print(f"Error get_semua_riwayat: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()