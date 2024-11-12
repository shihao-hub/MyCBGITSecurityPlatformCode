from tqdm import tqdm

with open("300mb_file.txt", "w", encoding="utf-8") as file:
    for i in tqdm(range(300 * 1024 * 1024)):
        file.write("a")
