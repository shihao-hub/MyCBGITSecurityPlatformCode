import base64
import logging
from typing import Optional

from Crypto.Cipher import AES

from django.conf import settings

logger = logging.getLogger("mylogger")


class CryptoHelper:
    MAX_AES_KEY_LENGTH = 16

    @staticmethod
    def add_to_16(value):
        """ str 不是 16 的倍数那就补足为 16 的倍数 """
        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)

    def __init__(self, cipher_key: Optional[str] = None, encoding="utf-8"):
        self._cipher_key = cipher_key if cipher_key else settings.SECRET_KEY[:type(self).MAX_AES_KEY_LENGTH]
        self._encoding = encoding

        # 初始化加密器
        self._aes = AES.new(type(self).add_to_16(self._cipher_key), AES.MODE_ECB)

    def encrypt(self, text: str):
        """ 生成密文 """
        encrypted_text_by_aes: bytes = self._aes.encrypt(type(self).add_to_16(text))
        encode_by_base64: bytes = base64.encodebytes(encrypted_text_by_aes)

        res: str = encode_by_base64.decode(encoding=self._encoding).strip()
        return res

    def decrypt(self, ciphertext: str):
        """ 解开密文 """
        decode_by_base64: bytes = base64.decodebytes(ciphertext.encode(encoding=self._encoding))
        decrypted_text_by_aes: bytes = self._aes.decrypt(decode_by_base64)

        res: str = decrypted_text_by_aes.decode(encoding="utf-8")
        return res
