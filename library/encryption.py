from cryptography.fernet import Fernet, InvalidToken
from library.logbook import LogBookHandler
import cryptography.fernet
import binascii
import base64
import os

logbook = LogBookHandler('encryption')

if os.path.exists('certs') is False:
    logbook.info("'certs' directory not found. Creating one...")
    os.makedirs('certs')

class encryption:
    class error:
        class NotEncrypted(Exception):
            def __init__(self, *args):
                super().__init__(*args)

    def __init__(self, key_file='certs/private.key'):
        self.key_file = key_file
        if not os.path.exists(key_file):
            self.generate_key()
        self.fernet_key = self.get_key()
        try:
            self.fernet = Fernet(self.fernet_key)
        except ValueError:
            err_msg = "The key file is empty or has been tampered with. Your data may be at risk."
            print(err_msg)
            logbook.warning(err_msg)

    def generate_key(self):
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as key_file:
            key_file.write(key)

    def get_key(self) -> bytes:
        with open(self.key_file, 'rb') as key_file:
            return key_file.read()

    def encrypt(self, message):
        if type(message) is None:
            raise ValueError("Cannot encrypt None!")

        encoded_message = message.encode('utf-8')
        try:
            encrypted_message = self.fernet.encrypt(encoded_message)
            return encrypted_message.decode('utf-8')
        except cryptography.fernet.InvalidToken:
            err_msg = "Invalid token problem while encrypting. The message may have been tampered with or you may be using the wrong private.key file."
            print(err_msg)
            logbook.warning(err_msg)
        except ValueError:
            err_msg = "The message is empty or the key has been tampered with."
            print(err_msg)
            logbook.warning(err_msg)

    def decrypt(self, encrypted_message):
        if encrypted_message is None:
            raise ValueError("Cannot decrypt None!")

        if not isinstance(encrypted_message, str):
            raise TypeError("The message is not a string.")

        # Try to detect if its actually a valid thing we can decrypt.
        # Step 1: Try to base64 decode it
        try:
            decoded = base64.urlsafe_b64decode(encrypted_message.encode("utf-8"))
        except (binascii.Error, ValueError):
            raise encryption.error.NotEncrypted("The message is not a valid Fernet token.")

        # Step 2: Check Fernet version byte (0x80)
        if len(decoded) == 0 or decoded[0] != 0x80:
            raise encryption.error.NotEncrypted("The string is not encrypted with Fernet.")

        # Step 3: Actually decrypt it
        try:
            decrypted_message = self.fernet.decrypt(encrypted_message.encode("utf-8"))
            return decrypted_message.decode("utf-8")

        except InvalidToken:
            err_msg = "Invalid token while decrypting. The message may have been tampered with or you may be using the wrong private.key file."
            print(err_msg)
            logbook.warning(err_msg)
            raise

        except ValueError:
            err_msg = "The message is empty or the key has been tampered with."
            print(err_msg)
            logbook.warning(err_msg)
            raise