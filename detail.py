import login

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import os
import json
import zipfile
from ricecooker.classes.files import HTMLZipFile, VideoFile, SubtitleFile, DownloadFile, AudioFile, DocumentFile
import requests.exceptions
import sys
import subprocess

session = login.session

class NotAZipFile(Exception):
    pass

try:
    os.mkdir("zipcache")
except FileExistsError:
    pass

sample_url="https://ca.pbslearningmedia.org/resource/vtl07.la.rv.text.cats/cats/"

def filename_from_url(url):
    return urlparse(url).path.strip("/").replace("/", "__")[-120:]  # e


def reencode(source_filename, file_format):    # TODO: refactor these non-mp4 hacks.
    # note: -n skips if file already exists, use -y to overwrite
    if file_format == "mp4":
        new_fn = source_filename + ".mp4"
        command = ["ffmpeg", "-i", source_filename, "-vcodec", "h264", "-acodec", "aac", "-strict", "2", 
                   "-crf", "24", "-y", "-hide_banner", "-loglevel", "warning", "-vf",
                   "scale=trunc(iw/2)*2:trunc(ih/2)*2", new_fn]
    elif file_format == "mp3":
        new_fn = source_filename + ".mp3"
        command = ["ffmpeg", "-i", source_filename, "-acodec", "mp3", "-ac", "2", "-ab", "192k", 
                   "-y", "-hide_banner", "-loglevel", "warning", new_fn]
    else:
        return None 

    if not os.path.exists(new_fn):
        subprocess.check_call(command)
        print("Successfully transcoded")
    else:
        print("... used cached file")
    return new_fn

def handle_video_zip(filename):
    try:
        archive = zipfile.ZipFile(filename)
    except zipfile.BadZipFile:
        raise  # TODO: add proper handling
    filenames = [zipped_file.filename for zipped_file in archive.filelist]
    name_and_size = [(zipped_file.filename, zipped_file.file_size) for zipped_file in archive.filelist]
    biggest = sorted(name_and_size, key = lambda x: x[1])[-1][0]
    
    for badname in ["deed.html", "readme.html", "license.html"]:
        try:
            filenames.remove(badname)
        except Exception:
            pass # if it's not there, we don't care

    for badname in [".m3u8", ".m3u", ".jpg", ".htm", ".html"]:
        for f in filenames:
            if f.endswith(badname):
                filenames.remove(f)

    if len(filenames)==0:
        raise NotAZipFile("contained no useful files") # TODO: handle better!
    elif len(filenames)==1:
        video_fn, = filenames
        subtitle_fn = None
    elif len(filenames) == 2:
        subtitle_fn = None
        video_fn = None
        for f in filenames:
            if f.endswith("vtt"):# or f.endswith("txt") or f.endswith('dxfp'):
                subtitle_fn = f
            else:
                video_fn = f
        if not (subtitle_fn and video_fn):
            # there are multiple video files? Assume the biggest is the one we want
            video_fn = biggest
            subtitle_fn = None
        
    else:
        # there are a lot of files
        # find the biggest file and a matching subtitle?
        video_fn = biggest
        subtitle_fn = None
        video_base_name = biggest[:-4]
        for f in filenames:
            if f.startswith(video_base_name) and f != video_fn:
                subtitle_fn = f
        
    video_ext = video_fn.split(".")[-1]
    if subtitle_fn:
        subtitle_ext = subtitle_fn.split(".")[-1]

    video_filename = filename + "__video."+video_ext

    with open(video_filename, 'wb') as f:
        f.write(archive.read(video_fn))
    
    # TODO: refactor these non-mp4 hacks.
    if video_ext != "mp4":
        video_filename = reencode(video_filename, "mp4")
 
    video_file_obj = VideoFile(video_filename, ffmpeg_settings={"crf":24})
    
    subtitle_file_obj = None
    if subtitle_fn:
        subtitle_filename = filename + "__subtitle." + subtitle_ext
        with open(subtitle_filename, 'wb') as f:
            f.write(archive.read(subtitle_fn))
        subtitle_file_obj = SubtitleFile(subtitle_filename, language='en')  # TODO: fix lang assumption!
        
    archive.close()
    return (video_file_obj, subtitle_file_obj)
        
def handle_simple_zip(filename, file_class, permitted_ext): # file_class = AudioFile for example
    try:
        archive = zipfile.ZipFile(filename)
    except zipfile.BadZipFile:
        raise  # TODO: add proper handling
    filenames = [zipped_file.filename for zipped_file in archive.filelist]
    for badname in ["deed.html", "readme.html", "license.html"]:
        try:
            filenames.remove(badname)
        except Exception:
            pass # if it's not there, we don't care

    assert len(filenames) in (1,), "Expected 1 file in {}, got {}".format(filename, filenames)
    fn, = filenames
        
    ext = fn.split(".")[-1]
    disk_filename = filename + "__audio."+ext # should probably be simple not audio TODO
    with open(disk_filename, 'wb') as f:
        f.write(archive.read(fn))
    
    if ext.lower() != permitted_ext: # this doesn't handle other types of file!
        print ("{} found, {} expected".format(ext, permitted_ext))
        disk_filename = reencode(disk_filename, permitted_ext)
    file_obj = file_class(disk_filename)
    
    return file_obj

def handle_audio_zip(filename):
    return handle_simple_zip(filename, AudioFile, "mp3")
    
def handle_doc_zip(filename):
    return handle_simple_zip(filename, DocumentFile, "docx")

def get_individual_page(item):
    # works for audio, individual images, 
    # downloading appears broken on website for "media gallery" (in images, documents...)
    # interactive things appear broken on website in entirety (and no download link)
    # webpages are just external links (many broken)
    # self-guided lessons - download broken, looks complex
    # lesson plan -- appears to not be its own thing, mostly. At least one is v. lon
    
    url = item['link']
    while True:
        try:
            response = session.get(url)
        except Exception as e:
            print (e)
        else:
            break
         
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise NotAZipFile()
    soup = BeautifulSoup(response.content, "html5lib")
    # TODO -- turn this into something useful.
    
    data = {}
    data['link'] = url
    data['title'] = item['title']
    content = soup.find("div", {'class': 'resource-content'})
    data['full_description'] = '\n'.join(tag.text.strip() for tag in content.findAll("p")).strip()  # TODO: contains too much junk.
    
    support = soup.findAll("div", {"class": "accordion-menu"}) 
    for accordion in support:  # Education is empty in source... TODO: remove it!
        #print(support)
        accordion_title = accordion.find("h2").text.strip()
        #print(accordion_title)
        subnodes = accordion.findAll("div", {"class": "collapsed"})
        
        for subnode in subnodes:
            subnode_title = subnode.find("h2").text.strip()
            #print("++ ", subnode_title)
            subnode_body = "\n".join(tag.text.strip() for tag in subnode.findAll("p")).strip()
            #print(repr(subnode_body))
    
    form = soup.find("form", {"id": "download_form"})
    target = urljoin(url, form.attrs['action'])

    # Note: redirection URL valid only for an hour or so.
    while True:
        try:
            zip_response = session.post(target, data={"agree": "on"}, stream=True)
        except Exception as e:
            print("problem with post", e)
        else:
            break
    filename = "zipcache/"+filename_from_url(url)+".zip"
    if not os.path.exists(filename):
        print ("Downloading zip to {}".format(filename))
        print ("{} bytes".format(zip_response.headers.get("content-length")))
        try:
            with open(filename, "wb") as f:
                # https://www.reddit.com/r/learnpython/comments/27ba7t/requests_library_doesnt_download_directly_to_disk/
                for chunk in zip_response.iter_content( chunk_size = 1024 ):
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
        except:  # Explicitly, we also want to catch CTRL-C here.
            print("Catching & deleting bad zip created by quitting")
            try:
                os.remove(filename)
            except:
                pass
            raise
            
            print ("{} bytes written".format(zip_response.headers.get("content-length")))
        with open(filename, "rb") as f:
            if f.read(2) != b"PK":
                print ("Removing bad zip file")
                os.remove(filename)

                raise NotAZipFile(filename)
    else:
        print ("... is cached as {}".format(filename))
            
    handlers = {"Video": handle_video_zip,
                "Audio": handle_audio_zip,
                #"Document": handle_doc_zip
               }
    if item['category'] in handlers:
        return handlers[item['category']](filename), data
    else:
        raise NotImplementedError(item['category'])

def download_category(category, filename, offset=-1):
    with open(filename) as f:
        database = [json.loads(line) for line in f.readlines()]
        
    i = 0
    for item in database:
        print (item)
        if item['category'] == category: # ["Video", "Document", "Audio", "Image", "Video"]
            print(category, i)
            i = i + 1
            if i < offset: continue
            try:
                nodes, data = get_individual_page(item)
            except NotAZipFile:
                continue


def download_videos(filename):
    download_category("Video", filename, offset=1689)

def download_audios(filename):
    download_category("Audio", filename, offset=-1)

#def download_docs(filename):
#    download_category("Document", filename, offset=-1)
    
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("add video or audio etc.")
    if 'video' in sys.argv:
        download_videos('share.json')
    if 'videom' in sys.argv:
        download_videos('modify.json')
    if 'audio' in sys.argv:
        download_audios('share.json')
#    if 'doc' in sys.argv:
#        download_docs('share.json')
    if 'audiom' in sys.argv:
        download_audios("modify.json")
#    if "docm" in sys.argv:
#        download_docs("modify.json")
#download_videos('modify.json')
#download_videos('download.json')

#get_individual_page("https://ca.pbslearningmedia.org/resource/4192684a-ae65-4c50-9f09-3925aabcfc88/vietnam-west-virginians-remember/#.WjARZ9-YHCI")

# get_individual_page("https://ca.pbslearningmedia.org/resource/754f0abf-0b58-4721-874b-44433c1a56d3/cat-and-rat", False)

#extensions = {'notebook', 'swf', 'png', 'jpg', 'dfxp', 'm3u8', 'm4v', 'docx', 'pdf', 'dxfp', 'doc', 'gif', '3gp', 'htm', 'flv', 'html', 'vtt', 'mov', 'epub', 'pptx', 'mp4', 'mp3', 'f4v', 'txt'}
