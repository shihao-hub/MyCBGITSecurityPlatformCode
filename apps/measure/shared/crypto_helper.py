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
        # (Q)!: 2024-11-11，这个的作用是啥？
        # str 不是 16 的倍数那就补足为 16 的倍数
        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)  # 返回bytes

    def __init__(self, key: Optional[str] = None):
        # 密钥
        self._key = key if key else settings.SECRET_KEY[:CryptoHelper.MAX_AES_KEY_LENGTH]

    def encrypt(self, text: str):
        """ 生成密文 """
        # 初始化加密器
        aes = AES.new(self.add_to_16(self._key), AES.MODE_ECB)
        # 进行 aes 加密
        encrypt_aes = aes.encrypt(self.add_to_16(text))
        # 用 base64 转成字符串形式
        encrypted_text = str(base64.encodebytes(encrypt_aes), encoding="utf-8")
        # 加密后的字符串会被添加换行符...
        encrypted_text = encrypted_text.strip()
        return encrypted_text

    def decrypt(self, ciphertext: str):
        """ 解开密文 """
        # 初始化加密器
        aes = AES.new(self.add_to_16(self._key), AES.MODE_ECB)
        # 逆向解密 base64 成 bytes
        base64_decrypted = base64.decodebytes(ciphertext.encode(encoding="utf-8"))
        # 执行解密密并转码返回 str
        decrypted_text = str(aes.decrypt(base64_decrypted), encoding="utf-8")
        return decrypted_text
