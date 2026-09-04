import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, flash
from features.dashboard import get_ringkasan_keuangan, get_semua_riwayat
from features.pencatatan import get_kategori_transaksi, simpan_transaksi_baru
from features.ocr import ekstraksi_total_struk
from features.auth import register_user, check_user_login
from datetime import timedelta

app = Flask(__name__)
# Secret key dibutuhkan untuk mengelola session login
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
            session.permanent = True  # <--- WAJIB DIPANGGIL agar durasi 30 hari aktif
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
            return redirect(url_for('login')) # balik ke login
        else:
            flash('Email sudah terdaftar. Silakan gunakan email lain.', 'danger')

    return render_template('register.html')

# --- MAIN APP ROUTES ---
@app.route('/')
@login_required
def index():
    user_id = session['user_id']
    data_dashboard = get_ringkasan_keuangan(user_id)
    return render_template('dashboard.html', data=data_dashboard)

@app.route('/tambah', methods=['GET', 'POST'])
@login_required
def tambah_transaksi():
    if request.method == 'POST':
        user_id = session['user_id']
        tipe = request.form.get('tipe')
        nominal = request.form.get('nominal')
        kategori = request.form.get('kategori')
        catatan = request.form.get('catatan')

        simpan_transaksi_baru(user_id, tipe, nominal, kategori, catatan)
        return redirect(url_for('index'))

    kategori = get_kategori_transaksi()
    return render_template('pencatatan.html', kategori=kategori)

@app.route('/transaksi')
@login_required
def transaksi():
    user_id = session['user_id']
    riwayat_lengkap = get_semua_riwayat(user_id)
    return render_template('transaksi.html', riwayat=riwayat_lengkap)

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

    nominal = ekstraksi_total_struk(file)
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