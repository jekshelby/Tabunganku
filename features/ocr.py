import requests
import re

def ekstraksi_total_struk(image_file):
    try:
        # Kirim file langsung ke Free OCR API
        payload = {
            'apikey': 'helloworld',  # API Key gratisan bawaan OCR.Space
            'language': 'eng',       # Angka di struk dibaca sama baiknya di eng/ind
            'isTable': True,
            'scale': True
        }
        
        files = {
            'file': (image_file.filename, image_file.stream, image_file.content_type)
        }
        
        response = requests.post('https://api.ocr.space/parse/image', files=files, data=payload)
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            print("OCR API Error:", result.get('ErrorMessage'))
            return 0
            
        teks = result['ParsedResults'][0]['ParsedText']
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
                    
        return nominal_ditemukan or 0

    except Exception as e:
        print(f"Error OCR API: {e}")
        return 0