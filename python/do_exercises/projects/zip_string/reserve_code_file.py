import os.path
import shutil

def reserve_code_file(src_dir, dest_dir):
    src_dir = src_dir.rstrip("\\/")
    dest_dir = dest_dir.rstrip("\\/")

    os_path_join = os.path.join

    for dirpath, subdirs, filenames in os.walk(src_dir):
        # os.path.join("c\","\d") 结果会有问题，不是 "c\d" ...
        rel_path = dirpath.replace(src_dir, "").lstrip("\\/")
        if rel_path.startswith((".venv", ".git", ".idea",)):
            continue
        os.mkdir(os_path_join(dest_dir, rel_path))

        for name in filenames:
            if name.endswith((".py", ".txt", ".bat", ".lua", ".html")):
                shutil.copy(str(os_path_join(dirpath, name)),
                            str(os_path_join(dest_dir, rel_path, name)))


# reserve_code_file(r"E:\Edtior_Projects\PyCharmProjects\do_exercises",
#                   r"E:\Edtior_Projects\PyCharmProjects\do_exercises\filter")
