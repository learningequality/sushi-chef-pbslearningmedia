import login

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import os
import json
session = login.session

try:
    os.mkdir("zipcache")
except FileExistsError:
    pass

sample_url="https://ca.pbslearningmedia.org/resource/vtl07.la.rv.text.cats/cats/"

def filename_from_url(url):
    return urlparse(url).path.strip("/").replace("/", "__")    

def get_video_page(url, get_video=True):
    # works for audio, individual images, 
    # downloading appears broken on website for "media gallery" (in images, documents...)
    # interactive things appear broken on website in entirety (and no download link)
    # webpages are just external links (many broken)
    # self-guided lessons - download broken, looks complex
    # lesson plan -- appears to not be its own thing, mostly. At least one is v. lon
    
    
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html5lib")
    # TODO -- turn this into something useful.
    
    data = {}
    data['link'] = url
    content = soup.find("div", {'class': 'resource-content'})
    data['full_description'] = '\n'.join(tag.text for tag in soup.findAll("p"))
    
    support = soup.findAll("div", {"class": "accordion-menu"}) 
    for accordion in support:  # Education is empty in source... TODO: remove it!
        print(support)
        accordion_title = accordion.find("h2").text.strip()
        print(accordion_title)
        subnodes = accordion.findAll("div", {"class": "collapsed"})
        
        for subnode in subnodes:
            subnode_title = subnode.find("h2").text.strip()
            print("++ ", subnode_title)
            subnode_body = "\n".join(tag.text.strip() for tag in subnode.findAll("p")).strip()
            print(repr(subnode_body))
    
    
    
    if get_video:
        form = soup.find("form", {"id": "download_form"})
        target = urljoin(url, form.attrs['action'])
    
        # Note: redirection URL valid only for an hour or so.
        zip_response = session.post(target, data={"agree": "on"}, stream=True)
        filename = "zipcache/"+filename_from_url(url)+".zip"
        if not os.path.exists(filename):
            print ("Downloading zip...")
            try:
                with open(filename, "wb") as f:
                    # https://www.reddit.com/r/learnpython/comments/27ba7t/requests_library_doesnt_download_directly_to_disk/
                    for chunk in zip_response.iter_content( chunk_size = 1024 ):
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
            except:  # Explicitly, we want to catch CTRL-C here.
                print("Catching...")
                try:
                    os.remove(filename)
                except:
                    pass
                raise
            
            print ("{} bytes written".format(zip_response.headers.get("content-length")))

    


#login.login()
#get_video_page(sample_url, get_video=False)

def download_videos(filename):
    with open(filename) as f:
        database = [json.loads(line) for line in f.readlines()]
        
    
    for item in database:
        if item['category'] in ("Document", "Audio", "Image", "Video"):
            get_video_page(item['link'])
    
download_videos('share.json')
download_videos('modify.json')
download_videos('download.json')

#get_video_page("https://ca.pbslearningmedia.org/resource/4192684a-ae65-4c50-9f09-3925aabcfc88/vietnam-west-virginians-remember/#.WjARZ9-YHCI")

# get_video_page("https://ca.pbslearningmedia.org/resource/754f0abf-0b58-4721-874b-44433c1a56d3/cat-and-rat", False)

#extensions = {'notebook', 'swf', 'png', 'jpg', 'dfxp', 'm3u8', 'm4v', 'docx', 'pdf', 'dxfp', 'doc', 'gif', '3gp', 'htm', 'flv', 'html', 'vtt', 'mov', 'epub', 'pptx', 'mp4', 'mp3', 'f4v', 'txt'}
