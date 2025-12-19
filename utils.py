# Cryptography imports
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import os, sqlite3

################################ Crypto Helpers ################################
def generate_key(master_password: str, salt: str = None) -> tuple[bytes, bytes]:
    """
    This function Generates Key to Encrypt and Decrypt Passwords
    IMP: same salt + same password will generate exact same key. but if one changes the key will change too.
    Args:
    1. master_password: This will be the master password that will be only know to the user.
    2. salt: This argument helps to add randomness in the kay that is generates
    Return:
    tuple[key(generated key), salt]
    """
    # generate a random 16-byte salt if not provided
    if salt:
        pass
    else:
        salt = os.urandom(16)
    # Use PBKDF2HMAC to derive a secure key from the password
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        # return derived key
        return kdf.derive(master_password.encode('utf-8')), salt
    except Exception as e:
        print(f"Unable to generate key: {e}")
        return

def encrypt_content(content: bytes, key: bytes) -> tuple[bytes, bytes]:
    """
    This Function will help us to encypt the content.
    IMP: you will not be able to decrypt data even if you have the key byt you don't give the same iv that is used in encryption.
    Args:
    1. content: this is a str that you want to encypt.
    2. key: this is the key that you have generated.
    Return:
    tuple[ecnrypted_content, iv(random inital vector to add extra security)]
    """
    try:
        # Generate a random 16-byte IV
        iv = os.urandom(16)
        # Create a Cipher object using the key and IV
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        # Encrypt the content
        encrypted_content = encryptor.update(content) + encryptor.finalize()
    except Exception as e:
        print(f"Unable to encrypt content: {e}")
        return
    return encrypted_content, iv

def decrypt_content(encrypted_content: bytes, key: bytes, iv: bytes) -> bytes:
    """
    This Function will deencypt the content that we have encrypted earlier.
    IMP: you will not be able to decrypt data even if you have the key if you don't give the same iv that was used in encryption.
    Args:
    1. encrypted_content: this encrypted data you want to deencypt.
    2. key: this is the key that you have generated.
    3. iv: this is the inital random vector that was used to encrypt the data.
    Return:
    decrypted_conetnt
    """
    try:
        # Create a Cipher object using the key and IV
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        # Decrypt the content
        decrypted_content = decryptor.update(encrypted_content) + decryptor.finalize()
        # Return the decrypted content as a string
        return decrypted_content
    except Exception as e:
        print(f"Unable to decrypt data: {e}")
        return
