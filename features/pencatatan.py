from db import get_db_connection

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

def simpan_transaksi_baru(user_id, tipe, nominal, kategori, catatan=""):
    """Menyimpan data transaksi baru khusus milik user_id tertentu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            INSERT INTO transaksi (user_id, tipe, nominal, kategori, catatan)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, tipe, nominal, kategori, catatan))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error simpan transaksi: {e}")
        return False
    finally:
        cursor.close()
        conn.close()