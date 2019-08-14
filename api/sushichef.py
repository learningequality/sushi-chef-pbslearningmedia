#!/usr/bin/env python
import os
import sys
sys.path.append(os.getcwd()) # Handle relative imports
import requests
from le_utils.constants import licenses
from ricecooker.classes.nodes import DocumentNode, VideoNode, AudioNode, TopicNode, Node
from ricecooker.classes.files import HTMLZipFile, VideoFile, SubtitleFile, DownloadFile
from ricecooker.chefs import SushiChef
import logging
import jsonlines
import tags

LOGGER = logging.getLogger()
MAX_NODE_LENGTH = 500

def use_rights(x):
    try:
        return "Share" in str(x['detail']['use_rights'])
    except Exception:
        return False

### Import index and filter for only shareable entries
with jsonlines.open("full.uniq.jsonlines") as reader:
    raw_index_data = list(reader)
index_data = list (x for x in raw_index_data if use_rights(x))
    
print ("Imported ", len(raw_index_data), " index entries")
print ("Using", len(index_data), " shareable index entries")

# Create list of leaf-tags.
# leaf_tags = {"audio": ['a', 'b'...], ...}
s_tags = list(tags.tags.keys())
s_tags.append("NOPE:NOPE")
leaf_tags = {}
old_tag = ""
for tag in s_tags:
    if old_tag in tag:
        pass
    else:
        pre, _, post = old_tag.partition(":")
        if pre not in leaf_tags:
            leaf_tags[pre] = []
        leaf_tags[pre].append(post)
    old_tag = tag
assert ("NOPE") not in leaf_tags


def first_letter(title):
    if title.upper().startswith("THE "):
        return first_letter(title[4:])
    if title.upper().startswith("A "):
        return first_letter(title[2:])
    
    for char in title.upper():
        if char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            return char
        if char in "01234567890":
            return "#"
    return "#" # no alphanumeric at all?
        
def audio_node(audio, data, license_type):
    print (data['title'])
    return AudioNode(source_id=data['link'],
                     title=data['title'],
                     description=data['full_description'], # TODO: see below
                     license = license_type,
                     copyright_holder="PBS Learning Media",
                     files = [audio,])

#def document_node(document, data, license_type):
#    print (data['title'])
#    if document.get_filename().lower().endswith(".pdf"):
#        node = DocumentNode
#    else:
#        node = DownloadNode
#        return node(source_id=data['link'],
#                        title=data['title'],
#                        description=data['full_description'], # TODO: see below
#                        license = license_type,
#                        copyright_holder="PBS Learning Media",
#                        files = [document,])


def video_node(video, subtitle, data, license_type):
    if subtitle:
        files = [video, subtitle]
    else:
        files = [video,]
    print (data['title'])
    return VideoNode(source_id=data['link'],
                     title=data['title'],
                     description=data['full_description'],  # TODO: get full descriptiom
                     license=license_type, 
                     copyright_holder="PBS Learning Media",
                     files=files,
                     )            
        


class PBS_API_Chef(SushiChef):
    # hierarchy = # open reverse.json and parse
    
    channel_info = {
        'CHANNEL_SOURCE_DOMAIN': 'pbslearningmedia.org', # who is providing the content (e.g. learningequality.org)
        'CHANNEL_SOURCE_ID': 'pbslearningmedia_api',         # channel's unique id
        'CHANNEL_TITLE': 'PBS Learning Media',
        'CHANNEL_LANGUAGE': 'en',                          # Use language codes from le_utils
        # 'CHANNEL_THUMBNAIL': 'https://im.openupresources.org/assets/im-logo.svg', # (optional) local path or url to image file
        'CHANNEL_DESCRIPTION': 'Bring Your Classroom to Life With PBS',  # (optional) description of the channel (optional)
    }

    def construct_channel(self, **kwargs):
        # code exists for:
        # "More" link
        # Collections
        # Alphabetical
    
        # create channel
        channel = self.get_channel(**kwargs)
        _index = TopicNode(source_id="collections",
                                     title = "Collections")
        channel.add_child(collection_index)
            
        return channel
 
def make_channel():
    mychef = PBS_API_Chef()
    args = {'token': os.environ['KOLIBRI_STUDIO_TOKEN'], 'reset': True, 'verbose': True}
    options = {}
    mychef.run(args, options)

make_channel()
