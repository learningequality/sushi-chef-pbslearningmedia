import login

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import os
import json
import zipfile
from ricecooker.classes.files import HTMLZipFile, VideoFile, SubtitleFile, DownloadFile, AudioFile
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
    return urlparse(url).path.strip("/").replace("/", "__")   

def handle_video_zip(filename):
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

    for badname in [".jpg", "placeholder"]:
        for f in filenames:
            if f.endswith(badname):
                filenames.remove(f)

    if len(filenames)==0:
        raise NotAZipFile("contained no useful files") # TODO: handle better!
    assert len(filenames) in (1,2), "Expected 1 or 2 files in {}, got {}".format(filename, filenames)
    if len(filenames) == 2:
        subtitle_fn = None
        video_fn = None
        for f in filenames:
            if f.endswith("vtt") or f.endswith("txt") or f.endswith('dxfp'):
                subtitle_fn = f
            else:
                video_fn = f
        if not (subtitle_fn and video_fn):
            # there are multiple video files! Choose one at random (the last one based on a sample of one
            # TODO: actually verify it's a video file and not eg. a gif.
            video_fn = filenames[-1]
            subtitle_fn = None
    else:
        video_fn, = filenames
        subtitle_fn = None
        
    video_ext = video_fn.split(".")[-1]
    if subtitle_fn:
        subtitle_ext = subtitle_fn.split(".")[-1]

    video_filename = filename + "__video."+video_ext

    with open(video_filename, 'wb') as f:
        f.write(archive.read(video_fn))
    
    # TODO: refactor these non-mp4 hacks.
    if video_ext != "mp4":
        mp4_fn = video_filename + ".mp4"
        command = ["ffmpeg", "-i", video_filename, "-vcodec", "h264", "-acodec", "aac", "-strict", "2", 
            "-crf", "24", "-y", mp4_fn]
        subprocess.check_call(command)
        print("Successfully transcoded")
        video_filename = mp4_fn 
      
    video_file_obj = VideoFile(video_filename, ffmpeg_settings={"crf":24})
    
    subtitle_file_obj = None
    if subtitle_fn:
        subtitle_filename = filename + "__subtitle." + subtitle_ext
        with open(subtitle_filename, 'wb') as f:
            f.write(archive.read(subtitle_fn))
        subtitle_file_obj = SubtitleFile(subtitle_filename, language='en')  # TODO: fix lang assumption!
        
    archive.close()
    return (video_file_obj, subtitle_file_obj)
        
def handle_audio_zip(filename):
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

    disk_filename = filename + "__audio."+ext
    with open(disk_filename, 'wb') as f:
        f.write(archive.read(fn))
    file_obj = AudioFile(disk_filename)
    
    return file_obj
    

def get_individual_page(item):
    # works for audio, individual images, 
    # downloading appears broken on website for "media gallery" (in images, documents...)
    # interactive things appear broken on website in entirety (and no download link)
    # webpages are just external links (many broken)
    # self-guided lessons - download broken, looks complex
    # lesson plan -- appears to not be its own thing, mostly. At least one is v. lon
    
    url = item['link']
    response = session.get(url)
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
    data['full_description'] = '\n'.join(tag.text.strip() for tag in soup.findAll("p")).strip()  # TODO: contains too much junk.
    
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
    zip_response = session.post(target, data={"agree": "on"}, stream=True)
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
                "Audio": handle_audio_zip}
    if item['category'] in handlers:
        return handlers[item['category']](filename), data
    else:
        raise NotImplementedError

#login.login()
#get_individual_page(sample_url, get_zip=False)
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
    download_category("Video", filename, offset=815)

def download_audios(filename):
    download_category("Audio", filename, offset=-1)


    
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("add video or audio etc.")
    if 'video' in sys.argv:
        download_videos('share.json')
    if 'audio' in sys.argv:
        download_audios('share.json')
#download_videos('modify.json')
#download_videos('download.json')

#get_individual_page("https://ca.pbslearningmedia.org/resource/4192684a-ae65-4c50-9f09-3925aabcfc88/vietnam-west-virginians-remember/#.WjARZ9-YHCI")

# get_individual_page("https://ca.pbslearningmedia.org/resource/754f0abf-0b58-4721-874b-44433c1a56d3/cat-and-rat", False)

#extensions = {'notebook', 'swf', 'png', 'jpg', 'dfxp', 'm3u8', 'm4v', 'docx', 'pdf', 'dxfp', 'doc', 'gif', '3gp', 'htm', 'flv', 'html', 'vtt', 'mov', 'epub', 'pptx', 'mp4', 'mp3', 'f4v', 'txt'}
