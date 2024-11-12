from PIL import Image
import tesserocr

data_and_validate = [
    {
        "path": "tesserocr_test_resources/pfrt.png",
        "correct_result": "pfrt"
    }
]

correct_count = 0

for dic in data_and_validate:
    path, correct_result = dic["path"], dic["correct_result"]
    image = Image.open(path)
    # image.show() # 调用图片应用程序打开图片
    image = image.convert("L")
    image = image.convert("1")
    # image.show()
    image = image.point([0 for _ in range(80)] + [1 for _ in range(80, 256)], "1")
    # image.show()
    if tesserocr.image_to_text(image).lower == correct_result:
        correct_result += 1

print("correct_percentage: {:.2f}%".format(correct_count / len(data_and_validate) * 100))
