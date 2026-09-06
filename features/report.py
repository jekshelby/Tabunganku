from datetime import date, datetime
from decimal import Decimal

from db import get_db_connection


def _period_range(period_type, period_value):
    if period_type == 'year':
        year = int(period_value)
        return date(year, 1, 1), date(year + 1, 1, 1)

    period = datetime.strptime(period_value, '%Y-%m')
    if period.month == 12:
        next_period = date(period.year + 1, 1, 1)
    else:
        next_period = date(period.year, period.month + 1, 1)
    return date(period.year, period.month, 1), next_period


def _buat_insight(pemasukan, pengeluaran, setor, kategori, target_tabungan):
    if not pemasukan and not pengeluaran and not setor:
        return {
            'judul': 'Belum ada aktivitas',
            'teks': 'Belum cukup data untuk membaca pola keuangan pada periode ini.',
            'ikon': 'bi-stars',
        }

    if pemasukan > pengeluaran:
        judul = 'Arus keuangan positif'
        teks = f'Pemasukan lebih besar dari pengeluaran sebesar Rp {pemasukan - pengeluaran:,.0f}.'.replace(',', '.')
    elif pengeluaran > pemasukan:
        judul = 'Perhatikan pengeluaran'
        teks = f'Pengeluaran lebih besar dari pemasukan sebesar Rp {pengeluaran - pemasukan:,.0f}.'.replace(',', '.')
    else:
        judul = 'Arus keuangan seimbang'
        teks = 'Pemasukan dan pengeluaran berada pada jumlah yang sama.'

    kategori_pengeluaran = next((item for item in kategori if item['tipe'] == 'pengeluaran'), None)
    if kategori_pengeluaran:
        teks += f" Pengeluaran terbesar berasal dari {kategori_pengeluaran['kategori']}."

    if setor:
        teks += f' Kamu menyisihkan Rp {setor:,.0f} ke tabungan.'.replace(',', '.')

    hampir_tercapai = next(
        (
            item for item in target_tabungan
            if item['target_nominal'] and item['saldo'] >= item['target_nominal'] * Decimal('0.8')
        ),
        None,
    )
    if hampir_tercapai:
        teks += f" Target {hampir_tercapai['nama']} sudah mendekati tujuan."

    return {'judul': judul, 'teks': teks, 'ikon': 'bi-lightbulb-fill'}


def get_laporan_keuangan(user_id, period_type='month', period_value=None):
    today = date.today()
    if period_type == 'year':
        period_value = period_value or str(today.year)
    else:
        period_type = 'month'
        period_value = period_value or today.strftime('%Y-%m')

    try:
        start_date, end_date = _period_range(period_type, period_value)
    except (TypeError, ValueError):
        period_type = 'month'
        period_value = today.strftime('%Y-%m')
        start_date, end_date = _period_range(period_type, period_value)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN LOWER(tipe) = 'pemasukan' THEN nominal ELSE 0 END), 0) AS pemasukan,
                    COALESCE(SUM(CASE WHEN LOWER(tipe) = 'pengeluaran' THEN nominal ELSE 0 END), 0) AS pengeluaran,
                    COUNT(*) AS jumlah_transaksi
                FROM transaksi
                WHERE user_id = %s AND tanggal >= %s AND tanggal < %s
                """,
                (user_id, start_date, end_date),
            )
            transaksi = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN tipe = 'setor' THEN nominal ELSE 0 END), 0) AS setor,
                    COALESCE(SUM(CASE WHEN tipe = 'tarik' THEN nominal ELSE 0 END), 0) AS tarik,
                    COUNT(*) AS jumlah_mutasi
                FROM transaksi_tabungan
                WHERE user_id = %s AND tanggal >= %s AND tanggal < %s
                """,
                (user_id, start_date, end_date),
            )
            tabungan = cursor.fetchone()

            cursor.execute(
                """
                SELECT kategori, LOWER(tipe) AS tipe, SUM(nominal) AS total
                FROM transaksi
                WHERE user_id = %s AND tanggal >= %s AND tanggal < %s
                GROUP BY kategori, LOWER(tipe)
                ORDER BY total DESC
                """,
                (user_id, start_date, end_date),
            )
            kategori = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    t.nama,
                    t.target_nominal,
                    t.status,
                    COALESCE(SUM(CASE WHEN tt.tipe = 'setor' THEN tt.nominal ELSE -tt.nominal END), 0) AS saldo
                FROM tabungan t
                LEFT JOIN transaksi_tabungan tt ON tt.tabungan_id = t.id
                WHERE t.user_id = %s
                GROUP BY t.id
                ORDER BY saldo DESC, t.created_at DESC
                """,
                (user_id,),
            )
            target_tabungan = cursor.fetchall()

        pemasukan = float(transaksi['pemasukan'])
        pengeluaran = float(transaksi['pengeluaran'])
        setor = float(tabungan['setor'])
        tarik = float(tabungan['tarik'])
        insight = _buat_insight(pemasukan, pengeluaran, setor, kategori, target_tabungan)
        return {
            'period_type': period_type,
            'period_value': period_value,
            'start_date': start_date,
            'end_date': end_date,
            'pemasukan': pemasukan,
            'pengeluaran': pengeluaran,
            'saldo_transaksi': pemasukan - pengeluaran,
            'setor': setor,
            'tarik': tarik,
            'arus_tabungan': setor - tarik,
            'jumlah_transaksi': transaksi['jumlah_transaksi'],
            'jumlah_mutasi': tabungan['jumlah_mutasi'],
            'kategori': kategori,
            'target_tabungan': target_tabungan,
            'insight': insight,
        }
    finally:
        conn.close()
