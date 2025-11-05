from Crypto.PublicKey import RSA

# Buat kunci privat baru 2048-bit
key = RSA.generate(2048)

# Ekspor dan simpan kunci privat
private_key = key.export_key()
with open("private_key.pem", "wb") as f:
    f.write(private_key)

# Ekspor dan simpan kunci publik
public_key = key.publickey().export_key()
with open("public_key.pem", "wb") as f:
    f.write(public_key)

print("Berhasil membuat 'private_key.pem' dan 'public_key.pem'.")
print("JANGAN PERNAH bagikan 'private_key.pem' Anda.")
