import os
all_files = os.listdir("zipcache")
zip_files = [x for x in all_files if x.endswith(".zip")]
bad = 0
for filename in zip_files:
    with open("zipcache/"+filename, "rb") as f:
        read = f.read(2)[:2]
        if read != b"PK":
            print(filename, read)
            os.remove("zipcache/"+filename)
            bad = bad + 1
print ("{} bad zip files found and removed".format(bad))
for filename in all_files:
    size = os.stat("zipcache/" + filename).st_size
    if size == 0:
        print(filename, 0)
