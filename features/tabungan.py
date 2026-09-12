from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import get_db_connection
from features.tautan import ambil_preview_tautan, normalisasi_url

_kolom_produk_siap = False
_PRODUK_FIELDS = 't.product_url, t.product_title, t.product_image, t.product_site'


def _ensure_kolom_produk(conn, cursor):
    global _kolom_produk_siap
    if _kolom_produk_siap:
        return
    cursor.execute(
        """
        ALTER TABLE tabungan
            ADD COLUMN IF NOT EXISTS product_url TEXT,
            ADD COLUMN IF NOT EXISTS product_title VARCHAR(300),
            ADD COLUMN IF NOT EXISTS product_image TEXT,
            ADD COLUMN IF NOT EXISTS product_site VARCHAR(100)
        """
    )
    conn.commit()
    _kolom_produk_siap = True


def _preview_dari_url(product_url):
    url = normalisasi_url(product_url)
    if not url:
        return '', '', '', ''
    preview = ambil_preview_tautan(url) or {}
    return (
        preview.get('url') or url,
        (preview.get('title') or '')[:300],
        (preview.get('image') or '')[:2000],
        (preview.get('site') or '')[:100],
    )


def _parse_nominal(value):
    try:
        nominal = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None
    nominal = nominal.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return nominal if nominal > 0 else None


def get_semua_tabungan(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            _ensure_kolom_produk(conn, cursor)
            cursor.execute(
                """
                SELECT
                    t.id,
                    t.nama,
                    t.target_nominal,
                    t.deadline,
                    t.status,
                    t.warna,
                    t.created_at,
                    """ + _PRODUK_FIELDS + """,
                    COALESCE(SUM(
                        CASE
                            WHEN tt.tipe = 'setor' THEN tt.nominal
                            WHEN tt.tipe = 'tarik' THEN -tt.nominal
                            ELSE 0
                        END
                    ), 0) AS saldo
                FROM tabungan t
                LEFT JOIN transaksi_tabungan tt ON tt.tabungan_id = t.id
                WHERE t.user_id = %s
                GROUP BY t.id
                ORDER BY
                    CASE WHEN t.status = 'aktif' THEN 0 ELSE 1 END,
                    t.created_at DESC
                """,
                (user_id,),
            )
            return cursor.fetchall()
    finally:
        conn.close()


def buat_tabungan(user_id, nama, target_nominal=None, deadline=None, warna='#1c1c1e', mode='target', product_url=''):
    nama = (nama or '').strip()
    target_input = (target_nominal or '').strip()
    target = _parse_nominal(target_input) if target_input else None
    if not nama or len(nama) > 100:
        return False, 'Nama tabungan wajib diisi dengan benar.'
    if target_input and not target:
        return False, 'Target nominal wajib diisi dengan benar.'
    if (product_url or '').strip() and not normalisasi_url(product_url):
        return False, 'Tautan produk tidak valid. Gunakan tautan http atau https.'

    product_url, product_title, product_image, product_site = _preview_dari_url(product_url)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            _ensure_kolom_produk(conn, cursor)
            cursor.execute(
                """
                INSERT INTO tabungan (
                    user_id, nama, target_nominal, deadline, warna,
                    product_url, product_title, product_image, product_site
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    nama,
                    target,
                    deadline or None,
                    warna or '#1c1c1e',
                    product_url or None,
                    product_title or None,
                    product_image or None,
                    product_site or None,
                ),
            )
            tabungan_id = cursor.fetchone()['id']
        conn.commit()
        return True, tabungan_id
    except Exception as error:
        conn.rollback()
        print(f'Error buat tabungan: {error}')
        return False, 'Tabungan gagal dibuat.'
    finally:
        conn.close()


def edit_target_tabungan(user_id, tabungan_id, nama, target_nominal=None, deadline=None, mode='target', product_url=''):
    nama = (nama or '').strip()
    target_input = (target_nominal or '').strip()
    target = _parse_nominal(target_input) if target_input else None
    if not nama or len(nama) > 100:
        return False, 'Nama tabungan wajib diisi dengan benar.'
    if target_input and not target:
        return False, 'Target nominal wajib diisi dengan benar.'
    if (product_url or '').strip() and not normalisasi_url(product_url):
        return False, 'Tautan produk tidak valid. Gunakan tautan http atau https.'

    product_url, product_title, product_image, product_site = _preview_dari_url(product_url)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            _ensure_kolom_produk(conn, cursor)
            cursor.execute(
                """
                SELECT COALESCE(SUM(
                    CASE WHEN tipe = 'setor' THEN nominal ELSE -nominal END
                ), 0) AS saldo
                FROM transaksi_tabungan
                WHERE tabungan_id = %s AND user_id = %s
                """,
                (tabungan_id, user_id),
            )
            saldo = cursor.fetchone()['saldo']
            cursor.execute(
                """
                UPDATE tabungan
                SET nama = %s,
                    target_nominal = %s,
                    deadline = %s,
                    product_url = %s,
                    product_title = %s,
                    product_image = %s,
                    product_site = %s,
                    status = CASE WHEN %s IS NOT NULL AND %s >= %s THEN 'tercapai' ELSE 'aktif' END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    nama,
                    target,
                    deadline or None,
                    product_url or None,
                    product_title or None,
                    product_image or None,
                    product_site or None,
                    target,
                    saldo,
                    target,
                    tabungan_id,
                    user_id,
                ),
            )
            updated = cursor.rowcount == 1
        conn.commit()
        return (True, 'Tabungan berhasil diperbarui.') if updated else (False, 'Tabungan tidak ditemukan.')
    except Exception as error:
        conn.rollback()
        print(f'Error edit target tabungan: {error}')
        return False, 'Target tabungan gagal diperbarui.'
    finally:
        conn.close()


def hapus_tabungan(user_id, tabungan_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nama,
                    COALESCE((
                        SELECT SUM(
                            CASE WHEN tipe = 'setor' THEN nominal ELSE -nominal END
                        )
                        FROM transaksi_tabungan
                        WHERE tabungan_id = tabungan.id AND user_id = %s
                    ), 0) AS saldo
                FROM tabungan
                WHERE id = %s AND user_id = %s
                FOR UPDATE
                """,
                (user_id, tabungan_id, user_id),
            )
            tabungan = cursor.fetchone()
            if not tabungan:
                return False, 'Tabungan tidak ditemukan.'

            cursor.execute(
                "SELECT id FROM dompet WHERE user_id = %s AND is_utama = TRUE ORDER BY id LIMIT 1",
                (user_id,),
            )
            cash_wallet = cursor.fetchone()
            if not cash_wallet:
                return False, 'Cash wallet tidak ditemukan.'

            if tabungan['saldo'] > 0:
                kategori = f"Pengembalian - {tabungan['nama']}"[:50]
                cursor.execute(
                    """
                    INSERT INTO transaksi (user_id, tipe, nominal, kategori, catatan, tabungan_id, dompet_id)
                    VALUES (%s, 'Pemasukan', %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        tabungan['saldo'],
                        kategori,
                        'Pengembalian saldo saat tabungan dihapus',
                        tabungan_id,
                        cash_wallet['id'],
                    ),
                )

            cursor.execute(
                'DELETE FROM tabungan WHERE id = %s AND user_id = %s',
                (tabungan_id, user_id),
            )
            deleted = cursor.rowcount == 1
        conn.commit()
        return (True, 'Tabungan dihapus dan saldonya dikembalikan ke saldo utama.') if deleted else (False, 'Tabungan tidak ditemukan.')
    except Exception as error:
        conn.rollback()
        print(f'Error hapus tabungan: {error}')
        return False, 'Tabungan gagal dihapus.'
    finally:
        conn.close()


def get_detail_tabungan(user_id, tabungan_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            _ensure_kolom_produk(conn, cursor)
            cursor.execute(
                """
                SELECT
                    t.id,
                    t.nama,
                    t.target_nominal,
                    t.deadline,
                    t.status,
                    t.warna,
                    t.created_at,
                    """ + _PRODUK_FIELDS + """,
                    COALESCE(SUM(
                        CASE
                            WHEN tt.tipe = 'setor' THEN tt.nominal
                            WHEN tt.tipe = 'tarik' THEN -tt.nominal
                            ELSE 0
                        END
                    ), 0) AS saldo
                FROM tabungan t
                LEFT JOIN transaksi_tabungan tt ON tt.tabungan_id = t.id
                WHERE t.id = %s AND t.user_id = %s
                GROUP BY t.id
                """,
                (tabungan_id, user_id),
            )
            tabungan = cursor.fetchone()
            if not tabungan:
                return None, []

            cursor.execute(
                """
                SELECT id, tipe, nominal, tanggal, catatan, created_at
                FROM transaksi_tabungan
                WHERE tabungan_id = %s AND user_id = %s
                ORDER BY tanggal DESC, created_at DESC
                """,
                (tabungan_id, user_id),
            )
            return tabungan, cursor.fetchall()
    finally:
        conn.close()


def simpan_mutasi_tabungan(user_id, tabungan_id, tipe, nominal, catatan=''):
    tipe = (tipe or '').strip().lower()
    nominal = _parse_nominal(nominal)
    if tipe not in {'setor', 'tarik'} or not nominal:
        return False, 'Jenis dan nominal mutasi tidak valid.'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nama, target_nominal, status,
                    COALESCE((
                        SELECT SUM(
                            CASE
                                WHEN tipe = 'setor' THEN nominal
                                ELSE -nominal
                            END
                        )
                        FROM transaksi_tabungan
                        WHERE tabungan_id = tabungan.id
                    ), 0) AS saldo
                FROM tabungan
                WHERE id = %s AND user_id = %s
                FOR UPDATE
                """,
                (tabungan_id, user_id),
            )
            tabungan = cursor.fetchone()
            if not tabungan:
                return False, 'Tabungan tidak ditemukan.'
            if tabungan['status'] == 'dibatalkan':
                return False, 'Tabungan yang dibatalkan tidak dapat diubah.'
            if tipe == 'tarik' and nominal > tabungan['saldo']:
                return False, 'Saldo tabungan tidak mencukupi.'

            cursor.execute(
                "SELECT id FROM dompet WHERE user_id = %s AND is_utama = TRUE ORDER BY id LIMIT 1",
                (user_id,),
            )
            cash_wallet = cursor.fetchone()
            if not cash_wallet:
                return False, 'Cash wallet tidak ditemukan.'

            cursor.execute(
                """
                INSERT INTO transaksi_tabungan
                    (tabungan_id, user_id, tipe, nominal, catatan)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (tabungan_id, user_id, tipe, nominal, (catatan or '').strip() or None),
            )
            mutation_id = cursor.fetchone()['id']

            kategori = f"Tabungan - {tabungan['nama']}"[:50]
            transaksi_tipe = 'Pengeluaran' if tipe == 'setor' else 'Pemasukan'
            transaksi_catatan = (catatan or '').strip() or f"{'Setor ke' if tipe == 'setor' else 'Tarik dari'} tabungan {tabungan['nama']}"
            cursor.execute(
                """
                INSERT INTO transaksi
                    (user_id, tipe, nominal, kategori, catatan, tabungan_id, dompet_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, transaksi_tipe, nominal, kategori, transaksi_catatan, tabungan_id, cash_wallet['id']),
            )

            saldo_baru = tabungan['saldo'] + (nominal if tipe == 'setor' else -nominal)
            status = (
                'tercapai'
                if tabungan['target_nominal'] is not None
                and saldo_baru >= tabungan['target_nominal']
                else 'aktif'
            )
            cursor.execute(
                "UPDATE tabungan SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (status, tabungan_id),
            )

        conn.commit()
        return True, 'Mutasi tabungan berhasil disimpan.'
    except Exception as error:
        conn.rollback()
        print(f'Error mutasi tabungan: {error}')
        return False, 'Mutasi tabungan gagal disimpan.'
    finally:
        conn.close()
