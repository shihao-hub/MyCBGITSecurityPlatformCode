import os
import re
import zipfile

ab = "ab"

zip_obj = zipfile.ZipFile("git_template.zip", "w")
for path, dirs, files in os.walk("git_template"):
    fpath = re.compile(r"^[^/\\]+[/\\]?").sub("", path)
    for filename in files:
        zip_obj.write(os.path.join(path, filename), os.path.join(fpath, filename))
zip_obj.close()
