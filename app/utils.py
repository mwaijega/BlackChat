from cryptography.fernet import Fernet

# Generate a key for encryption and decryption
def generate_key():
    return Fernet.generate_key()

# Initialize the Fernet object with the generated key
key = generate_key()
cipher_suite = Fernet(key)

def encrypt_message(message: str) -> str:
    return cipher_suite.encrypt(message.encode()).decode()

def decrypt_message(encrypted_message: str) -> str:
    return cipher_suite.decrypt(encrypted_message.encode()).decode()
