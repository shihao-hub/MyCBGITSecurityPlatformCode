import base64
from typing import Optional

from Crypto.Cipher import AES


class CryptoHelper:
    """ 采用AES对称加密算法 """
    MAX_AES_KEY_LENGTH = 16
    SECRET_KEY = "m2yb!j1u(o=7_!@-7ky9fbs+$=!t%l5s@tm)(i(-$11ylqr1r0"

    @staticmethod
    def add_to_16(value):
        """ str 不是 16 的倍数那就补足为 16 的倍数 """
        # 2024-11-12：注意事项，此处用的是 Zero 填充，可能会导致解密后的内容多出空格

        # 在使用对称加密算法（如AES）时，通常需要将明文填充到特定的块大小（例如16字节）。
        # 如果你的明文长度不是16的倍数，常用的做法是使用填充（padding）技术来确保其长度符合要求。

        # 填充方法：
        # PKCS#7填充：这是最常用的填充方式。在这种方式下，如果需要填充的字节数为n，则在明文末尾添加n个字节，每个字节的值都为n。
        # 例如，如果需要填充3个字节，则添加0x03 0x03 0x03。
        # Zero填充：在某些情况下，你可以选择用零填充，但这可能会导致解密时出现问题，因为原始数据中可能包含零字节。

        # 解密时去除填充：
        # 在解密时，你需要根据你使用的填充方式去除这些填充字节。
        # 例如，如果使用PKCS#7填充，你可以检查最后一个字节的值，确定有多少字节需要被去除。

        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)

    def __init__(self, cipher_key: Optional[str] = None, encoding="utf-8"):
        self._cls = type(self)

        self._cipher_key = cipher_key if cipher_key else CryptoHelper.SECRET_KEY[:CryptoHelper.MAX_AES_KEY_LENGTH]
        self._encoding = encoding

        # 初始化加密器
        self._aes = AES.new(CryptoHelper.add_to_16(self._cipher_key), AES.MODE_ECB)

    def encrypt(self, text: str):
        """ 生成密文 """
        # 2024-11-12：中文无法加密，报错提示：Data must be aligned to block boundary in ECB mode
        encrypted_text_by_aes: bytes = self._aes.encrypt(CryptoHelper.add_to_16(text))
        encode_by_base64: bytes = base64.encodebytes(encrypted_text_by_aes)

        res: str = encode_by_base64.decode(encoding=self._encoding).strip()
        return res

    def decrypt(self, ciphertext: str):
        """ 解开密文 """
        decode_by_base64: bytes = base64.decodebytes(ciphertext.encode(encoding=self._encoding))
        decrypted_text_by_aes: bytes = self._aes.decrypt(decode_by_base64)

        res: str = decrypted_text_by_aes.decode(encoding="utf-8")
        return res


def main():
    helper = CryptoHelper()

    to_be_encrypted_text = "Zsh"

    encrypted_text = helper.encrypt(to_be_encrypted_text)
    print(encrypted_text)

    decrypted_text = helper.decrypt(encrypted_text)
    print(decrypted_text)


if __name__ == '__main__':
    main()
