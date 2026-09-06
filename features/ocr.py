import os
import re
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def ekstraksi_total_struk(image_file):
    try:
        payload = {
            'apikey': os.getenv('OCR_SPACE_API_KEY', 'helloworld'),
            'language': 'eng',
            'isTable': True,
            'scale': True
        }
        
        response = None
        retryable_statuses = {429, 502, 503, 504}
        for attempt in range(3):
            image_file.stream.seek(0)
            files = {
                'file': (image_file.filename, image_file.stream, image_file.content_type)
            }
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files=files,
                data=payload,
                timeout=(10, 90),
            )
            if response.status_code not in retryable_statuses or attempt == 2:
                break

            retry_after = response.headers.get('Retry-After')
            try:
                wait_seconds = min(float(retry_after), 3) if retry_after else 1 + attempt
            except ValueError:
                wait_seconds = 1 + attempt
            print(
                f'OCR API sementara tidak tersedia ({response.status_code}); '
                f'mencoba lagi dalam {wait_seconds:g} detik.'
            )
            time.sleep(wait_seconds)

        if response.status_code in retryable_statuses:
            print(f'OCR API gagal setelah 3 percobaan: HTTP {response.status_code}')
            return None, 'Layanan OCR sedang sibuk. Tunggu sebentar lalu coba scan lagi.'

        response.raise_for_status()
        try:
            result = response.json()
        except ValueError:
            print('OCR API Error: response bukan JSON')
            return None, 'Layanan OCR mengembalikan respons yang tidak valid.'

        if result.get('IsErroredOnProcessing'):
            error_message = result.get('ErrorMessage') or result.get('ErrorDetails')
            if isinstance(error_message, list):
                error_message = ' '.join(str(item) for item in error_message)
            print('OCR API Error:', error_message)
            return None, str(error_message or 'Gambar gagal diproses oleh OCR.')

        parsed_results = result.get('ParsedResults') or []
        if not parsed_results or not parsed_results[0].get('ParsedText'):
            print('OCR API Error: ParsedResults kosong:', result)
            return None, 'Teks struk tidak berhasil dibaca. Coba foto lebih terang dan tidak buram.'

        teks = parsed_results[0]['ParsedText']
        print("--- TEKS STRUK (OCR.SPACE) ---")
        print(teks)
        print("------------------------------")
        
        baris_list = teks.upper().split('\r\n')
        nominal_ditemukan = None
        
        for baris in baris_list:
            if any(kw in baris for kw in ["TOTAL", "JUMLAH", "BAYAR", "GRAND TOTAL", "NET"]):
                angka_list = re.findall(r'\d+', baris)
                if angka_list:
                    gabung = int("".join(angka_list))
                    if gabung >= 500:
                        nominal_ditemukan = gabung
                        break
                        
        if not nominal_ditemukan:
            semua_angka = re.findall(r'\b\d{4,8}\b', teks)
            if semua_angka:
                daftar = [int(n) for n in semua_angka if int(n) >= 1000]
                if daftar:
                    nominal_ditemukan = max(daftar)
                    
        if not nominal_ditemukan:
            return None, 'Nominal total tidak ditemukan pada struk.'
        return nominal_ditemukan, None

    except requests.RequestException as e:
        print(f"Error koneksi OCR API: {e}")
        return None, 'Layanan OCR sedang tidak dapat dihubungi. Coba lagi beberapa saat.'
    except Exception as e:
        print(f"Error OCR API: {e}")
        return None, 'Terjadi kesalahan saat memproses struk.'