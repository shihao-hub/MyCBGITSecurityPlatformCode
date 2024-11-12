import re
import shutil
import traceback
from datetime import datetime
import os.path
import csv
import time
from os.path import basename, dirname
from hashlib import md5

UTF_8 = "utf-8"


class ZipFileCodec:
    _codec_types = {2: bin, 8: oct, 16: hex, 10: int}

    def __init__(self, pers_path="tmp_pers_path", codec_type=10, end_delete=False):
        self.file_slice_out_dir = None

        self.pers_path = os.path.splitext(pers_path)[0] + ".csv"
        self.end_delete = end_delete

        self.codec_type = codec_type
        self._check_codec_type()

    def _check_codec_type(self):
        if self.codec_type not in self._codec_types:
            raise Exception(f"codec_type({self.codec_type}) 必须在 {self._codec_types.keys()} 范围内")

    @classmethod
    def _check_zip_extension(cls, filepath: str):
        if not filepath.endswith(".zip"):
            raise Exception(f"{basename(filepath)} 的后缀必须是 .zip")

    def _encode_by_codec_type(self, val):
        if self.codec_type == 10:
            return str(val)
        return self._codec_types[self.codec_type](val)[2:]

    def encode(self, zip_file):
        self._check_zip_extension(zip_file)
        print(f"开始序列化 {basename(zip_file)} 文件")
        time_s = time.time()

        with open(zip_file, "rb") as file:
            with open(self.pers_path, "w", newline="") as fw:
                csv_writer = csv.writer(fw)
                # file.read() 迭代出来的就是 int，写入的时候会被转为字符串
                csv_writer.writerow(self._encode_by_codec_type(e) for e in file.read())

        print(f"序列化 {basename(zip_file)} 到 {basename(self.pers_path)} 文件中成功，"
              f"文件大小：{os.path.getsize(self.pers_path) / 1024 / 1024:.6f} MB，"
              f"耗时：{time.time() - time_s:.2f} s")

    def _decode_by_codec_type(self, val):
        return int(val, self.codec_type)

    def decode(self, zip_file):
        if not os.path.exists(self.pers_path):
            raise Exception("必须在 encode 函数之后执行该函数！")
        self._check_zip_extension(zip_file)

        print(f"开始反序列化 {basename(self.pers_path)} 文件")
        time_s = time.time()

        size = 0
        with open(self.pers_path, "r", newline="") as fr:
            csv_reader = csv.reader(fr)
            with open(zip_file, "wb") as fwb:
                for row in csv_reader:
                    for val in row:
                        size += 1
                        fwb.write(int.to_bytes(self._decode_by_codec_type(val), length=1, byteorder="big"))

        print(f"反序列化 {basename(self.pers_path)} 到 {basename(zip_file)} 文件中成功，"
              f"文件大小：{size / 1024 / 1024:.6f} MB，"
              f"耗时：{time.time() - time_s:.2f} s")

        if self.end_delete:
            os.remove(self.pers_path)

    @classmethod
    def file_slice(cls, target_file, per_size=1024 * 50) -> str:
        md5_obj = md5(datetime.now().strftime("%Y-%m-%d %H:%M:%S").encode("utf-8"))
        out_dir = md5_obj.hexdigest()
        # if os.path.exists(out_dir):
        #     shutil.rmtree(out_dir)
        os.makedirs(out_dir)
        with open(target_file, "r", encoding="utf-8") as fr:
            cnt = 0
            while True:
                data = fr.read(per_size)
                if not data:
                    break
                cnt += 1
                base_name, extension = os.path.splitext(os.path.basename(target_file))
                with open(os.path.join(out_dir, base_name + f"_{cnt}" + extension), "w", encoding="utf-8") as fw:
                    fw.write(data)
            print(f"文件切割完成，共切割出 {cnt} 个文件，其中每个文件的最大内存为：{per_size / 1024:.3f} KB")

        return out_dir

    @classmethod
    def file_reorganization(cls, files_dir) -> str:
        out_file = ""
        try:
            files = sorted(os.listdir(files_dir))
            out_file = re.sub(r"(.*)(_\d+?)(\.?.*)$", r"Reorganization_\1\3", os.path.basename(files[0]))
            with open(out_file, "w", encoding="utf-8") as fw:
                for name in files:
                    with open(os.path.join(files_dir, name), "r", encoding="utf-8") as fr:
                        fw.write(fr.read())
            print(f"文件重组结束")
        except:
            print(traceback.format_exc())
        finally:
            shutil.rmtree(files_dir)
        return out_file

    @staticmethod
    def test():
        zip_file_codec = ZipFileCodec("zip_test_out_binary")
        # zip_file_codec.encode(r"D:\games\Steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip")
        zip_file_codec.encode(r"markdowns.zip")
        zip_file_codec.decode("zip_test_out.zip")


if __name__ == '__main__':
    # zfc = ZipFileCodec("PyQt5Project_240628_1.csv", 15)
    # zfc.encode(r"C:\Users\zWX1333091\Desktop\PyQt5Project.zip")
    # zfc.decode(r"PyQt5Project_2.zip")

    # 此处为 PO，可以抽成类方法，变成 OO
    #   除此以外，这些变量总是一起出现，因此可以抽到一个类里面
    class Values:
        def __init__(self, pers_path, codec_type, in_zip_file, out_zip_file):
            self.pers_path = pers_path
            self.codec_type = codec_type
            self.in_zip_file = in_zip_file
            self.out_zip_file = out_zip_file


    values = Values(
        r"6月版本上线公告_v2_240701_1.csv",
        16,
        r"6月版本上线公告_v2.zip",
        r"6月版本上线公告_v2_2.zip"
    )

    zfc = ZipFileCodec(values.pers_path, values.codec_type)
    zfc.encode(values.in_zip_file)
    out_dir = zfc.file_slice(zfc.pers_path)
    zfc.file_reorganization(out_dir)
    zfc.decode(values.out_zip_file)
