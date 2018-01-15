import login

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import os
import json
import zipfile
from ricecooker.classes.files import HTMLZipFile, VideoFile, SubtitleFile, DownloadFile

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
    assert len(filenames) in (1,2), "Expected 1 or 2 files in {}, got {}".format(filename, filenames)
    if len(filenames) == 2:
        subtitle_fn = None
        video_fn = None
        for f in filenames:
            if f.endswith("vtt") or f.endswith("txt") or f.endswith('dxfp'):
                subtitle_fn = f
            else:
                video_fn = f
        assert subtitle_fn and video_fn, "{} has {}".format(filename, filenames)
    else:
        video_fn, = filenames
        subtitle_fn = None
        
    video_ext = video_fn.split(".")[-1]
    if subtitle_fn:
        subtitle_ext = subtitle_fn.split(".")[-1]

    video_filename = filename + "__video."+video_ext
    with open(video_filename, 'wb') as f:
        f.write(archive.read(video_fn))
    video_file_obj = VideoFile(video_filename, ffmpeg_settings={"crf":24})
    
    subtitle_file_obj = None
    if subtitle_fn:
        subtitle_filename = filename + "__subtitle." + subtitle_ext
        with open(subtitle_filename, 'wb') as f:
            f.write(archive.read(subtitle_fn))
        subtitle_file_obj = SubtitleFile(subtitle_filename, language='en')  # TODO: fix lang assumption!
        
    return (video_file_obj, subtitle_file_obj)
            
    archive.close()
        
    
        
    
    

def get_individual_page(item):
    # works for audio, individual images, 
    # downloading appears broken on website for "media gallery" (in images, documents...)
    # interactive things appear broken on website in entirety (and no download link)
    # webpages are just external links (many broken)
    # self-guided lessons - download broken, looks complex
    # lesson plan -- appears to not be its own thing, mostly. At least one is v. lon
    
    url = item['link']
    response = session.get(url)
    response.raise_for_status()
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
                raise NotAZipFile(filename)
    else:
        print ("... is cached as {}".format(filename))
            
    if item['category'] == "Video":
        return handle_video_zip(filename), data
    else:
        raise NotImplementedError

#login.login()
#get_individual_page(sample_url, get_zip=False)

def download_videos(filename):
    with open(filename) as f:
        database = [json.loads(line) for line in f.readlines()]
        
    i = 0
    for item in database:
        print (item)
        if item['category'] in ["Video"]: # ("Document", "Audio", "Image", "Video"):
            print(i)
            i = i + 1
            try:
                nodes, data = get_individual_page(item)
            except NotAZipFile:
                continue
            # print (nodes, data)
            #if i == 4:
            #    break
    
if __name__ == "__main__":
    download_videos('share.json')
#download_videos('modify.json')
#download_videos('download.json')

#get_individual_page("https://ca.pbslearningmedia.org/resource/4192684a-ae65-4c50-9f09-3925aabcfc88/vietnam-west-virginians-remember/#.WjARZ9-YHCI")

# get_individual_page("https://ca.pbslearningmedia.org/resource/754f0abf-0b58-4721-874b-44433c1a56d3/cat-and-rat", False)

#extensions = {'notebook', 'swf', 'png', 'jpg', 'dfxp', 'm3u8', 'm4v', 'docx', 'pdf', 'dxfp', 'doc', 'gif', '3gp', 'htm', 'flv', 'html', 'vtt', 'mov', 'epub', 'pptx', 'mp4', 'mp3', 'f4v', 'txt'}
