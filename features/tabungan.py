from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import get_db_connection


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


def buat_tabungan(user_id, nama, target_nominal, deadline=None, warna='#1c1c1e'):
    nama = (nama or '').strip()
    target = _parse_nominal(target_nominal)
    if not nama or len(nama) > 100 or not target:
        return False, 'Nama dan target tabungan wajib diisi dengan benar.'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tabungan (user_id, nama, target_nominal, deadline, warna)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, nama, target, deadline or None, warna or '#1c1c1e'),
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


def edit_target_tabungan(user_id, tabungan_id, nama, target_nominal, deadline=None):
    nama = (nama or '').strip()
    target = _parse_nominal(target_nominal)
    if not nama or len(nama) > 100 or not target:
        return False, 'Nama dan target tabungan wajib diisi dengan benar.'

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
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
                    status = CASE WHEN %s >= %s THEN 'tercapai' ELSE 'aktif' END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (nama, target, deadline or None, saldo, target, tabungan_id, user_id),
            )
            updated = cursor.rowcount == 1
        conn.commit()
        return (True, 'Target tabungan berhasil diperbarui.') if updated else (False, 'Tabungan tidak ditemukan.')
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

            if tabungan['saldo'] > 0:
                kategori = f"Pengembalian - {tabungan['nama']}"[:50]
                cursor.execute(
                    """
                    INSERT INTO transaksi (user_id, tipe, nominal, kategori, catatan, tabungan_id)
                    VALUES (%s, 'Pemasukan', %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        tabungan['saldo'],
                        kategori,
                        'Pengembalian saldo saat tabungan dihapus',
                        tabungan_id,
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
                    (user_id, tipe, nominal, kategori, catatan, tabungan_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, transaksi_tipe, nominal, kategori, transaksi_catatan, tabungan_id),
            )

            saldo_baru = tabungan['saldo'] + (nominal if tipe == 'setor' else -nominal)
            status = 'tercapai' if saldo_baru >= tabungan['target_nominal'] else 'aktif'
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
