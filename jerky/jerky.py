import os
import json
import md5

cache = {}

def freeze_cache(directory = "."):
    data = {}
    for root, dirs, files in os.walk(os.path.join(directory, ".ricecookerfilecache")):
        for name in files:
            cache_filename =  os.path.join(root, name)
            with open(cache_filename) as f:
                kolibri_hash = f.read().strip().partition(".")[0]
                data[name] = kolibri_hash
    with open("ricecache.json", "w") as f:
        json.dump(data, f)

def melt_cache():
    global cache
    with open("ricecache.json") as f:
        cache = f.read()

def check_cache(url):
    urlhash = md5.new(url).hexdigest()
    print (urlhash in cache)

melt_cache()
check_cache('')
