import zipfile
import os

DIR = "zipcache/"

zip_files = os.listdir(DIR)
all_contents = []
for zip_filename in zip_files:
    archive = zipfile.ZipFile(DIR+zip_filename)
    contents = [zipped_file.filename for zipped_file in archive.filelist]
    for badname in ["deed.html", "readme.html", "license.html"]:
        try:
            contents.remove(badname)
        except Exception:
            pass # if it's not there, we don't care
    all_contents.extend(contents)
    
extensions = set(x.partition('.')[2].lower() for x in all_contents)
print (extensions)
    
