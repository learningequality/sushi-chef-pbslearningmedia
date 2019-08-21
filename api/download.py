import login
import os
import lxml.html
import json
import add_file
session = login.session
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.98 Chrome/71.0.3578.98 Safari/537.36"
class NotAZipFile(Exception):
    pass

class NotAVideo(Exception):
    pass

try:
    os.mkdir("zipcache")
except FileExistsError:
    pass

def download_video_from_html(canonical_url, **kwargs):
    # download HTML
    response = session.get(canonical_url, headers={"user-agent": UA})
    root = lxml.html.fromstring(response.content)
    # get relevant script signature
    scripts= root.xpath("//script/text()")
    try:
        script, = [x for x in scripts if 'jwSettings1' in x]
    except Exception:
        raise NotAVideo("jwSettings1")
    # start at first `{`, end at first `\n};` for data structure};
    left = script.index("{")
    right = script.index("\n};")
    jsontext = script[left:right+2]
    j = json.loads(jsontext)
    primary_media, = [x for x in j['lo']['media'] if x['primary']]
    
    assert primary_media['url']
    video_filename, video_mime = add_file.download_file(primary_media['url'])
    video_node = add_file.create_node(filename=video_filename, **kwargs)

    if primary_media['caption']:
        try:
            caption_filename, caption_mime = add_file.download_file(primary_media['caption'])
        except add_file.UnidentifiedFileType:
            pass 
        else:
            caption_file = add_file.create_file(filename=caption_filename, **kwargs)
            video_node.add_file(caption_file)

    transcript_node = None
    # note: add .docx to guess_mime if you reenable this
    #if primary_media['transcript']:
    #    transcript_filename, transcript_mime = add_file.download_file(primary_media['transcript'])
    #    transcript_node = add_file.create_node(filename=transcript_filename, **kwargs)
    return video_node, transcript_node
