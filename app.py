import streamlit as st
import mysql.connector
from mysql.connector import Error
import os
from PIL import Image, UnidentifiedImageError
import bcrypt
# Import baru untuk Blowfish, RSA, dan AES (untuk hybrid)
from Crypto.Cipher import Blowfish, AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64
import numpy as np
import io
# Hapus 'tempfile' karena tidak digunakan
# import tempfile 
import json # Untuk menyimpan data hybrid RSA
import uuid # <-- BARU: Untuk nama file unik

# --- PENGATURAN KEAMANAN (KUNCI BARU) ---
# Kunci simetris (untuk Blowfish) dari Env Var
APP_SYMMETRIC_KEY = os.environ.get("APP_SYMMETRIC_KEY")
if not APP_SYMMETRIC_KEY:
    # Fallback untuk pengembangan lokal jika env var tidak diatur
    APP_SYMMETRIC_KEY = "kunci_rahasia_blowfish_lokal_32"
    # st.warning("PERINGATAN: APP_SYMMETRIC_KEY tidak diatur. Menggunakan kunci fallback lokal.")
    # (Dalam produksi, baris di bawah ini harus diaktifkan)
    # st.error("FATAL: APP_SYMMETRIC_KEY tidak diatur di environment variables!")
    # st.stop()

# --- PERSIAPAN FOLDER UPLOADS ---
# Pastikan folder 'uploads' ada
os.makedirs("uploads", exist_ok=True)
# -----------------------------------

# Muat kunci publik RSA (Aman untuk didistribusikan)
try:
    rsa_public_key = RSA.import_key(open("public_key.pem").read())
except FileNotFoundError:
    st.error("FATAL: File 'public_key.pem' tidak ditemukan. Pastikan file tersebut ada di folder yang sama.")
    st.stop()
# KUNCI PRIVAT RSA HANYA AKAN DIMUAT DI SISI ADMIN
# ----------------------------------------------------

# Session state initialization
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Login"

# Database connection helper
def create_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="pengaduan2"
        )
        return connection if connection.is_connected() else None
    except Error as e:
        st.error(f"Gagal terhubung ke database: {e}")
    return None

# --- HASHING (BCRYPT) & ENKRIPSI ---

def hash_password_bcrypt(password):
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def check_password_bcrypt(password, hashed_password):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

# --- Algoritma Hybrid Vigenere + XOR ---

def encrypt_vigenere(plain_text, key):
    key = key.upper()
    encrypted_text = ""
    key_index = 0
    for char in plain_text:
        if char.isalpha():
            shift_base = ord('A') if char.isupper() else ord('a')
            shift = ord(key[key_index % len(key)]) - ord('A')
            encrypted_text += chr((ord(char) - shift_base + shift) % 26 + shift_base)
            key_index += 1
        else:
            encrypted_text += char
    return encrypted_text

def decrypt_vigenere(cipher_text, key):
    key = key.upper()
    decrypted_text = ""
    key_index = 0
    for char in cipher_text:
        if char.isalpha():
            shift_base = ord('A') if char.isupper() else ord('a')
            shift = ord(key[key_index % len(key)]) - ord('A')
            decrypted_text += chr((ord(char) - shift_base - shift) % 26 + shift_base)
            key_index += 1
        else:
            decrypted_text += char
    return decrypted_text

def encrypt_xor(plain_text, key):
    """Enkripsi/Dekripsi XOR sederhana."""
    encrypted_text = ""
    for i in range(len(plain_text)):
        key_c = key[i % len(key)]
        encrypted_text += chr(ord(plain_text[i]) ^ ord(key_c))
    return encrypted_text

# XOR adalah simetris, enkripsi dan dekripsi sama
decrypt_xor = encrypt_xor

# --- Algoritma Blowfish (Pengganti AES) ---

def encrypt_blowfish(data_bytes):
    """Enkripsi Blowfish (menerima bytes) menggunakan kunci global. Menghasilkan string Base64."""
    try:
        # Kunci Blowfish bisa 4-56 bytes. Kita ambil 56.
        key = pad(APP_SYMMETRIC_KEY.encode(), 8)[:56] # 8 adalah block_size, tapi kita pad dulu
        iv = get_random_bytes(Blowfish.block_size) # Block size Blowfish = 8 bytes
        cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv)
        # Pad data ke 8-byte block
        raw = pad(data_bytes, Blowfish.block_size)
        encrypted_data = iv + cipher.encrypt(raw)
        return base64.b64encode(encrypted_data).decode('utf-8')
    except Exception as e:
        st.error(f"Error enkripsi Blowfish: {e}")
        return None

def decrypt_blowfish(encrypted_text_str):
    """Dekripsi Blowfish (menerima string Base64) menggunakan kunci global. Menghasilkan bytes."""
    try:
        key = pad(APP_SYMMETRIC_KEY.encode(), 8)[:56]
        encrypted_data = base64.b64decode(encrypted_text_str)
        iv = encrypted_data[:Blowfish.block_size]
        ciphertext = encrypted_data[Blowfish.block_size:]
        cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv)
        # Unpad data dari 8-byte block
        decrypted_data = unpad(cipher.decrypt(ciphertext), Blowfish.block_size)
        return decrypted_data
    except Exception as e:
        print(f"Decryption error (Blowfish): {str(e)}")
        # Mengembalikan None atau string error dalam bentuk bytes
        return b"Gagal Mendekripsi Data (Blowfish)"

# --- Algoritma Super Encrypt (Vigenere -> XOR -> Blowfish) ---
# (Digunakan untuk Kronologi)

def super_encrypt(text, vigenere_key, xor_key):
    # 1. Vigenere
    vigenere_encrypted = encrypt_vigenere(text, vigenere_key)
    # 2. XOR
    xor_encrypted = encrypt_xor(vigenere_encrypted, xor_key)
    # 3. Blowfish
    # Kita meng-encode hasil XOR ke bytes sebelum mengenkripsi
    return encrypt_blowfish(xor_encrypted.encode('utf-8'))

def super_decrypt(encrypted_text_str, vigenere_key, xor_key):
    try:
        # 1. Blowfish (Hasilnya adalah bytes)
        blowfish_decrypted_bytes = decrypt_blowfish(encrypted_text_str)
        
        if blowfish_decrypted_bytes == b"Gagal Mendekripsi Data (Blowfish)":
                return "Error: Gagal dekripsi Blowfish"

        # Decode bytes hasil dekripsi Blowfish ke string (hasil XOR)
        xor_encrypted_text = blowfish_decrypted_bytes.decode('utf-8')
        
        # 2. XOR
        xor_decrypted = decrypt_xor(xor_encrypted_text, xor_key)
        # 3. Vigenere
        return decrypt_vigenere(xor_decrypted, vigenere_key)
    except Exception as e:
        return f"Error dekripsi: {str(e)}"

# --- FUNGSI FILE HANDLING & LSB ---

def display_image_from_data(image_data_bytes):
    try:
        if isinstance(image_data_bytes, bytes):
            image = Image.open(io.BytesIO(image_data_bytes))
            st.image(image, use_container_width=True)
        else:
            st.error("Data gambar tidak valid (bukan bytes).")
    except Exception as e:
        st.error(f"Error displaying image: {e}")

def display_file_download(file_data, file_name, file_type):
    try:
        mime_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        file_extension = file_name.split('.')[-1].lower()
        mime_type = mime_types.get(file_extension, 'application/octet-stream')
        
        st.download_button(
            label=f"Download {file_name}",
            data=file_data,
            file_name=file_name,
            mime=mime_type
        )
    except Exception as e:
        st.error(f"Error creating download button: {e}")

# ---
# FUNGSI LSB (STEGANOGRAPHY)
# (Digunakan untuk Judul + Foto)
# ---

def embed_message(image, message):
    """
    Menyisipkan pesan ke dalam gambar (LSB).
    Perbaikan: pastikan dtype uint8, gunakan mask 0xFE (254) bukan ~1.
    """
    try:
        rgb_image = image.convert("RGB")
    except Exception as e:
        raise ValueError(f"Gagal mengkonversi gambar ke RGB: {e}")

    message += "####"  # penanda akhir
    binary_message = ''.join(format(ord(char), '08b') for char in message)
    message_len = len(binary_message)

    # Pastikan menggunakan uint8 untuk mencegah masalah overflow/underflow
    image_data = np.array(rgb_image, dtype=np.uint8)
    flat_image = image_data.flatten()

    if message_len > flat_image.size:
        raise ValueError("Pesan terlalu panjang untuk dimasukkan ke dalam gambar.")

    # Sisipkan bit satu per satu — gunakan mask 0xFE (11111110) bukan ~1
    for i in range(message_len):
        bit = int(binary_message[i])
        val = int(flat_image[i])        # convert ke Python int aman
        val = (val & 0xFE) | bit        # clear LSB lalu set sesuai bit
        flat_image[i] = np.uint8(val)   # pastikan kembali ke uint8

    new_image_data = flat_image.reshape(image_data.shape)
    return Image.fromarray(new_image_data.astype('uint8'))

def extract_message(image):
    """
    Mengekstrak pesan dari gambar (LSB).
    """
    try:
        rgb_image = image.convert("RGB")
        image_data = np.array(rgb_image, dtype=np.uint8)
    except Exception as e:
        st.error(f"Gagal membaca data LSB (konversi RGB gagal): {e}")
        return "[Error: Gagal konversi RGB]"

    flat_image = image_data.flatten()
    # Ambil LSB dari tiap byte
    binary_bits = [str(int(b) & 1) for b in flat_image]

    # Gabungkan tiap 8 bit menjadi karakter
    chars = [''.join(binary_bits[i:i+8]) for i in range(0, len(binary_bits), 8)]
    decoded = ''
    for byte in chars:
        if len(byte) != 8:
            continue
        val = int(byte, 2)
        # hanya masukkan karakter valid
        if val == 0:
            # mungkin padding, abaikan
            continue
        
        # Coba tambahkan karakter
        try:
            decoded += chr(val)
        except:
            # Gagal decode (mungkin akhir dari data), abaikan
            pass
            
        # optional: jika sudah ketemu penanda, bisa break lebih awal
        if decoded.endswith("####"):
            return decoded[:-4]

    # Jika tidak ditemukan penanda, mungkin ada noise. Coba cari lagi.
    if "####" in decoded:
        return decoded.split("####")[0]

    return None # Tidak ditemukan
# --- FUNGSI ENKRIPSI FILE (RSA HYBRID) ---
# (Digunakan untuk File Bukti)

def encrypt_file(file_data_bytes):
    """Enkripsi file menggunakan metode Hybrid Encryption (RSA + AES-GCM). Menghasilkan BYTES (JSON string)."""
    try:
        session_key = get_random_bytes(16)
        cipher_aes = AES.new(session_key, AES.MODE_GCM)
        ciphertext, tag = cipher_aes.encrypt_and_digest(file_data_bytes)
        nonce = cipher_aes.nonce
        cipher_rsa = PKCS1_OAEP.new(rsa_public_key)
        encrypted_session_key = cipher_rsa.encrypt(session_key)

        encrypted_package = {
            'key': base64.b64encode(encrypted_session_key).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'tag': base64.b64encode(tag).decode('utf-8'),
            'data': base64.b64encode(ciphertext).decode('utf-8')
        }
        # Mengembalikan sebagai BYTES
        return json.dumps(encrypted_package).encode('utf-8')
        
    except Exception as e:
        st.error(f"Error enkripsi file (hybrid): {e}")
        return None

def decrypt_file(encrypted_data_blob):
    """Dekripsi file (Hybrid Encryption). MEMBUTUHKAN 'private_key.pem'. Menerima BYTES (JSON string)."""
    try:
        try:
            private_key = RSA.import_key(open("private_key.pem").read())
        except FileNotFoundError:
            st.error("FATAL: File 'private_key.pem' rahasia tidak ditemukan di server.")
            return None
        
        # Menerima BYTES, jadi kita decode dulu
        encrypted_package = json.loads(encrypted_data_blob.decode('utf-8'))
        
        encrypted_session_key = base64.b64decode(encrypted_package['key'])
        nonce = base64.b64decode(encrypted_package['nonce'])
        tag = base64.b64decode(encrypted_package['tag'])
        ciphertext = base64.b64decode(encrypted_package['data'])

        cipher_rsa = PKCS1_OAEP.new(private_key)
        session_key = cipher_rsa.decrypt(encrypted_session_key)

        cipher_aes = AES.new(session_key, AES.MODE_GCM, nonce)
        decrypted_data = cipher_aes.decrypt_and_verify(ciphertext, tag)
        
        return decrypted_data

    except (ValueError, KeyError, FileNotFoundError) as e:
        st.error(f"Gagal mendekripsi file: {e}. Data mungkin korup atau kunci salah.")
        return None

# --- FUNGSI UTAMA APLIKASI ---

def register_user(nama, username, email, password):
    password_hashed = hash_password_bcrypt(password)
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT * FROM user WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                return False
            cursor.execute("INSERT INTO user (nama, username, email, password) VALUES (%s, %s, %s, %s)",
                           (nama, username, email, password_hashed))
            connection.commit()
            return True
        except Error as e:
            st.error(f"Terjadi kesalahan: {e}")
        finally:
            cursor.close()
            connection.close()
    return False

def login_user(username, password):
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True) 
        try:
            cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user and check_password_bcrypt(password, user['password']):
                st.session_state.is_logged_in = True
                st.session_state.user_data = user
                return user
        except Error as e:
            st.error(f"Terjadi kesalahan: {e}")
        finally:
            cursor.close()
            connection.close()
    return None

def save_pengaduan(id_pelapor, judul_pengaduan, kronologi_terenkripsi_str, foto_filename, file_filename=None):
    """
    PERUBAHAN: Menyimpan NAMA FILE (string) ke database, bukan data blob.
    """
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO aduan (id_pelapor, judul_pengaduan, kronologi, bukti_foto, bukti_file)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    # 'judul_pengaduan' tetap dikirim, meskipun "TIDAK DIGUNAKAN"
                    (id_pelapor, judul_pengaduan, kronologi_terenkripsi_str, foto_filename, file_filename)
                )
                connection.commit()
                return True
            except Error as e:
                # Ini adalah tempat error Anda muncul
                st.error(f"Terjadi kesalahan saat menyimpan ke database: {e}")
                return False
            finally:
                cursor.close()
                connection.close()
    except Exception as e:
        st.error(f"Terjadi kesalahan saat menyimpan pengaduan: {e}")
        return False

def logout():
    st.session_state.is_logged_in = False
    st.session_state.user_data = None
    st.session_state.current_page = "Login"

def login_admin(username, password):
    # Metode login 'hardcoded' (tidak disarankan untuk produksi)
    if username == "admin" and password == "admin":
        st.session_state.is_logged_in = True
        st.session_state.user_data = {'nama': 'Admin', 'id': 0, 'role': 'admin'} # Menambahkan role
        st.session_state.current_page = "Admin"
        return True
    return False

# --- HALAMAN (PAGES) ---

def admin_page():
    st.title("Dashboard Admin")
    connection = create_connection()

    if connection:
        st.subheader("Tabel User")
        try:
            cursor = connection.cursor(dictionary=True) 
            cursor.execute("SELECT id, nama, username, email FROM user") # Menghapus 'role' jika belum di-implementasi
            users = cursor.fetchall()
            if users:
                st.dataframe(users)
            else:
                st.info("Tidak ada data user")
            cursor.close()
        except Error as e:
            st.error(f"Error saat mengambil data user: {e}")

        st.subheader("Daftar Aduan")
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.id_laporan, a.id_pelapor, a.judul_pengaduan, a.kronologi, 
                       a.bukti_foto, a.bukti_file, u.nama as nama_pelapor
                FROM aduan a 
                LEFT JOIN user u ON a.id_pelapor = u.id
                ORDER BY a.id_laporan DESC
            """)
            results = cursor.fetchall()

            if results:
                # Input kunci dekripsi (diperlukan untuk kronologi)
                st.info("Masukkan kunci Vigenere & XOR untuk mendekripsi kronologi.")
                col_v, col_x = st.columns(2)
                v_key = col_v.text_input("Kunci Vigenere (Admin)", key="admin_v_key")
                x_key = col_x.text_input("Kunci XOR (Admin)", key="admin_x_key")

                for row in results:
                    
                    decrypted_judul = "[Gagal Dekripsi Judul]"
                    decrypted_foto_bytes = None # Penting: untuk menampung bytes foto
                    
                    # 1. PERUBAHAN: Baca file foto dari disk, lalu dekripsi
                    try:
                        if row['bukti_foto']: # Ini sekarang NAMA FILE
                            filename_foto = row['bukti_foto'] # <-- PERBAIKAN BUG: Sebelumnya 'bukti_file'

                            # --- FIX: Decode bytes ke string ---
                            if isinstance(filename_foto, bytes):
                                filename_foto = filename_foto.decode('utf-8')
                            # --- END FIX ---
                            
                            file_path_foto = os.path.join("uploads", filename_foto)

                            if os.path.exists(file_path_foto):
                                # 1. Baca string terenkripsi dari file
                                with open(file_path_foto, 'r', encoding='utf-8') as f:
                                    stego_image_string = f.read()
                                
                                # 2. Lapisan 1: Dekripsi Blowfish (Hasil: bytes gambar LSB)
                                decrypted_foto_bytes = decrypt_blowfish(stego_image_string)
                                
                                if decrypted_foto_bytes != b"Gagal Mendekripsi Data (Blowfish)":
                                    # 3. Lapisan 2: Ekstrak pesan LSB dari bytes gambar
                                    image_lsb = Image.open(io.BytesIO(decrypted_foto_bytes))
                                    decrypted_judul = extract_message(image_lsb)
                                    
                                    if not decrypted_judul:
                                        decrypted_judul = "[Judul tidak ditemukan di LSB]"
                                else:
                                    decrypted_judul = "[Foto LSB Gagal Dekripsi]"
                            else:
                                decrypted_judul = f"[File Foto Hilang: {filename_foto}]"

                        else:
                             decrypted_judul = "[Tidak ada bukti foto]"

                    except Exception as e:
                        decrypted_judul = f"[Error LSB: {e}]"

                    # Judul expander sekarang menggunakan judul yang sudah didekripsi
                    expander_title = f"Laporan #{row['id_laporan']} - {decrypted_judul} (oleh: {row['nama_pelapor']})"

                    with st.expander(expander_title, expanded=False):
                        try:
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.subheader(f"Judul: {decrypted_judul}")
                                
                                # 2. Dekripsi Teks (Super Decrypt: Blowfish -> XOR -> Vigenere)
                                # Tidak ada perubahan di sini, 'kronologi' masih data langsung
                                st.write("**Kronologi:**")
                                if v_key and x_key:
                                    decrypted_kronologi = super_decrypt(row['kronologi'], v_key, x_key)
                                    st.write(decrypted_kronologi)
                                else:
                                    st.warning("Masukkan Kunci Vigenere dan XOR di atas untuk melihat kronologi.")
                            
                            with col2:
                                # Tampilkan Foto (jika berhasil didekripsi)
                                if decrypted_foto_bytes: # Cek jika bytes-nya ada
                                    st.write("**Bukti Foto (Stego-Image):**")
                                    display_image_from_data(decrypted_foto_bytes)
                                
                                # 3. PERUBAHAN: Baca file dari disk, lalu dekripsi
                                if row['bukti_file']: # Ini sekarang NAMA FILE
                                    st.write("**Bukti File:**")
                                    try:
                                        filename_file = row['bukti_file']

                                        # --- FIX: Decode bytes ke string ---
                                        if isinstance(filename_file, bytes):
                                            filename_file = filename_file.decode('utf-8')
                                        # --- END FIX ---

                                        file_path_file = os.path.join("uploads", filename_file)

                                        if os.path.exists(file_path_file):
                                            # 1. Baca string terenkripsi dari file
                                            with open(file_path_file, 'r', encoding='utf-8') as f:
                                                file_string_encrypted = f.read()

                                            # 2. Lapisan 1: Dekripsi Blowfish (Hasil: bytes RSA Hybrid)
                                            decrypted_hybrid_blob = decrypt_blowfish(file_string_encrypted)
                                            
                                            if decrypted_hybrid_blob != b"Gagal Mendekripsi Data (Blowfish)":
                                                # 3. Lapisan 2: Dekripsi RSA Hybrid
                                                decrypted_file_data = decrypt_file(decrypted_hybrid_blob)
                                                
                                                if decrypted_file_data:
                                                    # Coba tebak nama file asli dari ekstensi
                                                    original_name_parts = filename_file.split('.')
                                                    ext = original_name_parts[-2] if len(original_name_parts) > 2 else 'dat'
                                                    file_name_download = f"laporan_{row['id_laporan']}_bukti.{ext}"
                                                    display_file_download(decrypted_file_data, file_name_download, "application/octet-stream")
                                                else:
                                                    st.error("Gagal dekripsi file (Lapisan Hybrid).")
                                            else:
                                                st.error("Gagal dekripsi file (Lapisan Blowfish).")
                                        else:
                                            st.error(f"File {filename_file} tidak ditemukan di server.")
                                            
                                    except Exception as e:
                                        st.error(f"Gagal memproses file: {e}")
                                
                        except Exception as e:
                            st.error(f"Error memproses laporan #{row['id_laporan']}: {e}")
                            
            else:
                st.info("Tidak ada data pengaduan untuk ditampilkan.")
            
            cursor.close()
        except Error as e:
            st.error(f"Terjadi kesalahan saat mengambil data aduan: {e}")
        finally:
            connection.close()

    if st.button("Logout"):
        logout()
        st.rerun()


def login_page():
    st.title("Login")
    with st.form(key='login_form'):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if login_admin(username, password):
                st.success("Login sebagai Admin berhasil!")
                st.rerun()
            else:
                user = login_user(username, password)
                if user:
                    st.session_state.current_page = "Pengaduan"
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau password salah!")
    
    if st.button("Belum punya akun? Register"):
        st.session_state.current_page = "Register"
        st.rerun()


def register_page():
    st.title("Register")
    with st.form(key='register_form'):
        nama = st.text_input("Nama Lengkap")
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Register"):
            if register_user(nama, username, email, password):
                st.success("Registrasi berhasil! Silakan login.")
                st.session_state.current_page = "Login"
                st.rerun()
            else:
                st.error("Username atau email sudah digunakan.")
    
    if st.button("Sudah punya akun? Login"):
        st.session_state.current_page = "Login"
        st.rerun()


def pengaduan_page():
    st.title("Halaman Pengaduan")
    
    nama_pelapor = st.session_state.user_data.get('nama', 'User Tidak Dikenal')
    id_pelapor = st.session_state.user_data.get('id')

    if not id_pelapor:
        st.error("Sesi Anda tidak valid, silakan login kembali.")
        logout()
        st.rerun()
        return

    with st.form(key='pengaduan_form'):
        st.text_input("Nama Pelapor", value=nama_pelapor, disabled=True)
        judul_pengaduan = st.text_input("Judul Pengaduan")
        kronologi = st.text_area("Kronologi Pengaduan")
        
        st.info("Kunci Vigenere & XOR digunakan untuk mengenkripsi Kronologi Anda. HARAP SIMPAN KUNCI INI!")
        col_v, col_x = st.columns(2)
        v_key = col_v.text_input("Kunci Vigenere", help="Hanya gunakan huruf (A-Z). Contoh: 'RAHASIA'")
        x_key = col_x.text_input("Kunci XOR", help="Bisa kombinasi apapun. Contoh: 'kunci123'")

        bukti_foto = st.file_uploader("Upload Bukti Foto (WAJIB)", type=["jpg", "png", "jpeg"], help="Judul pengaduan akan disembunyikan di dalam foto ini.")
        bukti_file = st.file_uploader("Upload File Bukti (PDF/TXT/DOCX)", type=["pdf", "txt", "docx"])

        if st.form_submit_button("Kirim Pengaduan"):
            
            # Validasi input
            if not (judul_pengaduan and kronologi and v_key and x_key and bukti_foto):
                st.error("Harap isi semua kolom: Judul, Kronologi, Kunci Vigenere, Kunci XOR, dan Bukti Foto (Wajib).")
                return # Hentikan eksekusi

            try:
                # --- ALUR ENKRIPSI ---
                
                # Buat ID unik untuk file-file ini
                unique_id = uuid.uuid4()

                # 1. JUDUL + FOTO (LSB -> Blowfish -> Simpan ke File)
                stego_image_string = None
                filename_foto = None
                try:
                    foto_data_bytes = bukti_foto.read()
                    image = Image.open(io.BytesIO(foto_data_bytes))
                    # Lapisan 1: LSB (Menyisipkan judul ke gambar)
                    stego_image = embed_message(image, judul_pengaduan)
                    
                    # Ubah stego_image (objek PIL) kembali ke bytes
                    img_byte_arr = io.BytesIO()
                    stego_image.save(img_byte_arr, format='PNG') # Simpan sebagai PNG (lossless)
                    stego_image_bytes = img_byte_arr.getvalue()

                    # Lapisan 2: Enkripsi Blowfish (Hasil: String Base64)
                    stego_image_string = encrypt_blowfish(stego_image_bytes)

                    # PERUBAHAN: Simpan string ini ke file, jangan ke DB
                    filename_foto = f"foto_{id_pelapor}_{unique_id}.png.enc"
                    file_path_foto = os.path.join("uploads", filename_foto)
                    with open(file_path_foto, 'w', encoding='utf-8') as f:
                        f.write(stego_image_string)

                except Exception as e:
                    st.error(f"Error memproses LSB gambar: {e}")
                    # Hentikan jika LSB (yang wajib) gagal
                    raise ValueError(f"Terjadi kesalahan fatal saat proses enkripsi foto: {e}")

                # 2. KRONOLOGI (Vigenere -> XOR -> Blowfish)
                # (Ini teks, ukurannya kecil, aman disimpan di DB)
                kronologi_string = super_encrypt(kronologi, v_key, x_key)

                # 3. FILE (RSA Hybrid -> Blowfish -> Simpan ke File)
                filename_file = None # Default
                if bukti_file:
                    file_data_bytes = bukti_file.read()
                    # Lapisan 1: RSA Hybrid (Hasil: bytes)
                    file_hybrid_bytes = encrypt_file(file_data_bytes)
                    
                    if file_hybrid_bytes:
                        # Lapisan 2: Enkripsi Blowfish (Hasil: String Base64)
                        file_string = encrypt_blowfish(file_hybrid_bytes)
                        
                        # PERUBAHAN: Simpan string ini ke file
                        file_extension = bukti_file.name.split('.')[-1]
                        filename_file = f"file_{id_pelapor}_{unique_id}.{file_extension}.enc"
                        file_path_file = os.path.join("uploads", filename_file)
                        with open(file_path_file, 'w', encoding='utf-8') as f:
                            f.write(file_string)
                    else:
                        st.warning("Gagal mengenkripsi file bukti, file tidak akan dilampirkan.")


                # PERUBAHAN: Simpan NAMA FILE ke database
                if save_pengaduan(id_pelapor, "TIDAK DIGUNAKAN", kronologi_string, filename_foto, filename_file):
                    st.success(f"Pengaduan berhasil dikirim! (Judul '{judul_pengaduan}' telah disisipkan ke dalam gambar).")
                    # Tambahan: Kosongkan form? (Opsional)
                else:
                    # Error sudah ditampilkan oleh save_pengaduan()
                    st.error("Pengaduan gagal dikirim.")
            
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
    
    if st.button("Logout"):
        logout()
        st.rerun()


# Fungsi utama (Router)
def main():
    if not st.session_state.is_logged_in:
        if st.session_state.current_page == "Register":
            register_page()
        else:
            login_page()
    else:
        # Jika sudah login
        user_role = st.session_state.user_data.get('role')
        if user_role == 'admin' and st.session_state.current_page == "Admin":
            admin_page()
        elif user_role != 'admin' and st.session_state.current_page == "Pengaduan":
            pengaduan_page()
        else:
            # Skenario fallback jika terjadi ketidaksesuaian
            logout()
            st.rerun()

if __name__ == "__main__":
    main()