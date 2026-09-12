import os
from functools import wraps
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, flash

from features.dashboard import get_ringkasan_keuangan, get_semua_riwayat
from features.pencatatan import (
    edit_transaksi,
    get_kategori_transaksi,
    get_transaksi,
    hapus_transaksi,
    simpan_transaksi_baru,
)
from features.ocr import ekstraksi_total_struk
from features.auth import (
    check_user_login,
    get_user_profile,
    register_user,
    update_user_profile,
)
from features.report import get_laporan_keuangan
from features.dompet import buat_dompet, get_dompet_options, hapus_dompet
from features.tagihan import bayar_tagihan, buat_tagihan, get_semua_tagihan, hapus_tagihan
from features.tabungan import (
    buat_tabungan,
    edit_target_tabungan,
    get_detail_tabungan,
    get_semua_tabungan,
    hapus_tabungan,
    simpan_mutasi_tabungan,
)
from features.tautan import ambil_preview_tautan

app = Flask(__name__)

# Secret key untuk mengelola session login
app.secret_key = os.getenv('SECRET_KEY', 'catatuang_secret_key_12345')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# --- DECORATOR PROTEKSI ROUTE ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTHENTICATION ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = check_user_login(email, password)
        if user:
            session.permanent = True  # Aktifkan session 30 hari
            session['user_id'] = user['id']
            session['user_nama'] = user['nama']
            return redirect(url_for('index'))
        else:
            flash('Email atau password salah!', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nama = request.form.get('nama')
        email = request.form.get('email')
        password = request.form.get('password')

        success, result = register_user(nama, email, password)
        if success:
            flash('Pendaftaran berhasil! Silakan masuk dengan akun baru kamu.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email sudah terdaftar. Silakan gunakan email lain.', 'danger')

    return render_template('register.html')

# --- MAIN APP ROUTES ---
@app.route('/')
@login_required
def index():
    user_id = session['user_id']

    # 1. Ambil ringkasan angka (saldo, pemasukan, pengeluaran)
    data_dashboard = get_ringkasan_keuangan(user_id) or {}

    # 2. Ambil seluruh riwayat
    riwayat_raw = get_semua_riwayat(user_id)

    # 3. Proses riwayat untuk preview 3 item di Dashboard (apabila return-nya dict/list)
    items_flat = []
    if isinstance(riwayat_raw, dict):
        # Jika riwayat berupa dictionary di-group per tanggal
        for tanggal, group in riwayat_raw.items():
            for item in group.get('items', []):
                # Masukkan tanggal ke item agar bisa dipanggil item.tanggal
                item_with_date = item.copy()
                item_with_date['tanggal'] = tanggal
                items_flat.append(item_with_date)
    elif isinstance(riwayat_raw, list):
        # Jika riwayat berupa list biasa
        items_flat = riwayat_raw

    # Simpan maksimal 3 transaksi terbaru untuk index.html
    data_dashboard['riwayat'] = items_flat[:3]

    return render_template('dashboard.html', data=data_dashboard)

@app.route('/tambah', methods=['GET', 'POST'])
@login_required
def tambah_transaksi():
    user_id = session['user_id']
    if request.method == 'POST':
        tipe = request.form.get('tipe')
        nominal = request.form.get('nominal')
        kategori = request.form.get('kategori')
        catatan = request.form.get('catatan')
        dompet_id = request.form.get('dompet_id') or None
        dompet_tujuan_id = request.form.get('dompet_tujuan_id') or None

        if simpan_transaksi_baru(user_id, tipe, nominal, kategori, catatan, dompet_id, dompet_tujuan_id):
            flash('Transaksi berhasil disimpan.', 'success')
            return redirect(url_for('index'))

        flash('Transaksi tidak valid atau gagal disimpan.', 'danger')
        return redirect(url_for('tambah_transaksi'))

    kategori = get_kategori_transaksi()
    return render_template('pencatatan.html', kategori=kategori, dompet=get_dompet_options(user_id))

@app.route('/transaksi')
@login_required
def transaksi():
    user_id = session['user_id']
    riwayat_lengkap = get_semua_riwayat(user_id) or {}

    return render_template('transaksi.html', riwayat=riwayat_lengkap)

@app.route('/report')
@login_required
def report():
    period_type = request.args.get('periode', 'month')
    period_value = request.args.get('nilai')
    data_report = get_laporan_keuangan(session['user_id'], period_type, period_value)
    return render_template('report.html', report=data_report)

@app.route('/akun', methods=['GET', 'POST'])
@login_required
def akun():
    user_id = session['user_id']
    if request.method == 'POST':
        success, message = update_user_profile(
            user_id,
            request.form.get('nama'),
            request.form.get('email'),
            request.form.get('password') or None,
        )
        if success:
            session['user_nama'] = request.form.get('nama', '').strip()
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('akun'))
    return render_template('akun.html', profile=get_user_profile(user_id))

@app.route('/dompet', methods=['POST'])
@login_required
def tambah_dompet():
    success, result = buat_dompet(
        session['user_id'],
        request.form.get('nama'),
        request.form.get('jenis'),
        request.form.get('warna'),
    )
    flash('Dompet berhasil ditambahkan.' if success else result, 'success' if success else 'danger')
    return redirect(url_for('index'))

@app.route('/dompet/<int:dompet_id>/hapus', methods=['POST'])
@login_required
def hapus_dompet_route(dompet_id):
    success, message = hapus_dompet(session['user_id'], dompet_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('index'))

@app.route('/tagihan', methods=['GET', 'POST'])
@login_required
def tagihan():
    user_id = session['user_id']
    if request.method == 'POST':
        success, result = buat_tagihan(
            user_id,
            request.form.get('nama'),
            request.form.get('nominal'),
            request.form.get('jatuh_tempo'),
            request.form.get('kategori'),
            request.form.get('catatan'),
        )
        flash('Tagihan berhasil dibuat.' if success else result, 'success' if success else 'danger')
        return redirect(url_for('tagihan'))
    return render_template('tagihan.html', tagihan=get_semua_tagihan(user_id), dompet=get_dompet_options(user_id))

@app.route('/tagihan/<int:tagihan_id>/bayar', methods=['POST'])
@login_required
def bayar_tagihan_route(tagihan_id):
    success, message = bayar_tagihan(session['user_id'], tagihan_id, request.form.get('dompet_id'))
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tagihan'))

@app.route('/tagihan/<int:tagihan_id>/hapus', methods=['POST'])
@login_required
def hapus_tagihan_route(tagihan_id):
    success, message = hapus_tagihan(session['user_id'], tagihan_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tagihan'))

@app.route('/transaksi/<int:transaksi_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaksi_route(transaksi_id):
    user_id = session['user_id']
    transaksi_data = get_transaksi(user_id, transaksi_id)
    if not transaksi_data:
        flash('Transaksi tidak ditemukan.', 'danger')
        return redirect(url_for('transaksi'))
    if transaksi_data['tabungan_id'] is not None:
        flash('Transaksi tabungan dikelola dari menu Tabungan.', 'danger')
        return redirect(url_for('transaksi'))
    if transaksi_data.get('dompet_tujuan_id') is not None or (transaksi_data.get('tipe') or '').strip().lower() == 'alokasi dana':
        flash('Alokasi dana tidak dapat diedit. Buat alokasi baru jika perlu menyesuaikan.', 'danger')
        return redirect(url_for('transaksi'))

    if request.method == 'POST':
        success = edit_transaksi(
            user_id,
            transaksi_id,
            request.form.get('tipe'),
            request.form.get('nominal'),
            request.form.get('kategori'),
            request.form.get('catatan'),
        )
        flash(
            'Transaksi berhasil diperbarui.' if success else 'Data transaksi tidak valid.',
            'success' if success else 'danger',
        )
        return redirect(url_for('transaksi'))

    return render_template(
        'transaksi_edit.html',
        transaksi=transaksi_data,
        kategori=get_kategori_transaksi(),
    )

@app.route('/transaksi/<int:transaksi_id>/hapus', methods=['POST'])
@login_required
def hapus_transaksi_route(transaksi_id):
    success = hapus_transaksi(session['user_id'], transaksi_id)
    flash(
        'Transaksi berhasil dihapus.' if success else 'Transaksi tidak ditemukan.',
        'success' if success else 'danger',
    )
    return redirect(url_for('transaksi'))

@app.route('/tabungan', methods=['GET'])
@login_required
def tabungan():
    return render_template('tabungan.html', tabungan=get_semua_tabungan(session['user_id']))

@app.route('/tabungan/baru', methods=['GET', 'POST'])
@login_required
def tambah_tabungan():
    user_id = session['user_id']
    if request.method == 'POST':
        success, result = buat_tabungan(
            user_id,
            request.form.get('nama'),
            request.form.get('target_nominal'),
            request.form.get('deadline'),
            request.form.get('warna'),
            request.form.get('mode', 'target'),
            request.form.get('product_url'),
        )
        if success:
            flash('Tabungan berhasil dibuat.', 'success')
            return redirect(url_for('detail_tabungan', tabungan_id=result))
        flash(result, 'danger')
        return redirect(url_for('tambah_tabungan'))
    return render_template('tabungan_create.html')

@app.route('/api/preview-tautan')
@login_required
def api_preview_tautan():
    preview = ambil_preview_tautan(request.args.get('url', ''))
    if not preview:
        return jsonify({'success': False, 'message': 'Tautan tidak valid.'}), 400
    return jsonify({'success': True, **preview})

@app.route('/tabungan/<int:tabungan_id>')
@login_required
def detail_tabungan(tabungan_id):
    tabungan_data, mutasi = get_detail_tabungan(session['user_id'], tabungan_id)
    if not tabungan_data:
        flash('Tabungan tidak ditemukan.', 'danger')
        return redirect(url_for('tabungan'))
    return render_template('tabungan_detail.html', tabungan=tabungan_data, mutasi=mutasi)

@app.route('/tabungan/<int:tabungan_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tabungan_route(tabungan_id):
    user_id = session['user_id']
    tabungan_data, _ = get_detail_tabungan(user_id, tabungan_id)
    if not tabungan_data:
        flash('Tabungan tidak ditemukan.', 'danger')
        return redirect(url_for('tabungan'))

    if request.method == 'POST':
        success, message = edit_target_tabungan(
            user_id,
            tabungan_id,
            request.form.get('nama'),
            request.form.get('target_nominal'),
            request.form.get('deadline'),
            request.form.get('mode', 'target'),
            request.form.get('product_url'),
        )
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('detail_tabungan', tabungan_id=tabungan_id))

    return render_template('tabungan_edit.html', tabungan=tabungan_data)

@app.route('/tabungan/<int:tabungan_id>/hapus', methods=['POST'])
@login_required
def hapus_tabungan_route(tabungan_id):
    success, message = hapus_tabungan(session['user_id'], tabungan_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tabungan'))

@app.route('/tabungan/<int:tabungan_id>/mutasi', methods=['POST'])
@login_required
def mutasi_tabungan(tabungan_id):
    success, message = simpan_mutasi_tabungan(
        session['user_id'],
        tabungan_id,
        request.form.get('tipe'),
        request.form.get('nominal'),
        request.form.get('catatan'),
    )
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('detail_tabungan', tabungan_id=tabungan_id))

@app.route('/scan')
@login_required
def scan_ocr():
    return render_template('scan.html')

@app.route('/api/scan-ocr', methods=['POST'])
@login_required
def api_scan_ocr():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Tidak ada file diunggah'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'File kosong'}), 400

    nominal, error_message = ekstraksi_total_struk(file)
    if error_message:
        return jsonify({'success': False, 'message': error_message}), 502

    return jsonify({
        'success': True,
        'nominal': nominal
    })

# --- PWA & STATIC ASSETS ---
@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)