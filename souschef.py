#!/usr/bin/env python
import os
import sys
sys.path.append(os.getcwd()) # Handle relative imports
import requests
from le_utils.constants import licenses
from ricecooker.classes.nodes import DocumentNode, VideoNode, AudioNode
from ricecooker.classes.files import HTMLZipFile, VideoFile, SubtitleFile, DownloadFile
from ricecooker.chefs import SushiChef
import logging
import detail
import json 


LOGGER = logging.getLogger()


class PBSChef(SushiChef):
    channel_info = {
        'CHANNEL_SOURCE_DOMAIN': 'pbslearningmedia.org', # who is providing the content (e.g. learningequality.org)
        'CHANNEL_SOURCE_ID': 'pbslearningmedia',         # channel's unique id
        'CHANNEL_TITLE': 'PBS Learning Media',
        'CHANNEL_LANGUAGE': 'en',                          # Use language codes from le_utils
        # 'CHANNEL_THUMBNAIL': 'https://im.openupresources.org/assets/im-logo.svg', # (optional) local path or url to image file
        'CHANNEL_DESCRIPTION': 'Bring Your Classroom to Life With PBS',  # (optional) description of the channel (optional)
    }

    def construct_channel(self, **kwargs):
        def audio_node(audio, data, license_type):
            print (data['title'])
            return AudioNode(source_id=data['link'],
                             title=data['title'],
                             description=data['full_description'], # TODO: see below
                             license = license_type,
                             copyright_holder="PBS Learning Media",
                             files = [audio,])

        def document_node(document, data, license_type):
            print (data['title'])
            if document.get_filename().lower().endswith(".pdf"):
                node = DocumentNode
            else:
                node = DownloadNode
                return node(source_id=data['link'],
                                title=data['title'],
                                description=data['full_description'], # TODO: see below
                                license = license_type,
                                copyright_holder="PBS Learning Media",
                                files = [document,])


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
        

    
        # create channel
        channel = self.get_channel(**kwargs)
        # create a topic and add it to channel
        data = {}
        
#        for doc, data in download_docs("share.json"):
#            channel.add_child(document_node(doc, data, licenses.CC_BY_NC_ND)) # was _SA
        for audio, data in download_audios("share.json"):
            channel.add_child(audio_node(audio, data, licenses.CC_BY_NC_ND)) # was _SA
        for (video, subtitle), data in download_videos("share.json"):
            channel.add_child(video_node(video, subtitle, data, licenses.CC_BY_NC_ND)) # was _SA
        return channel

    
def download_category(category, jsonfile, make_unique=False):
    with open(jsonfile) as f:
        if make_unique:
            # for some reason there are some duplicates in the database -- probably due to pagination issues when crawling.
            lines = set(f.readlines())
        else:
            lines = f.readlines()
    database = [json.loads(line) for line in lines]
    for item in database:
        if item['category'] == category: #  ["Video"]: # ("Document", "Audio", "Image", "Video"):
            try:
                yield detail.get_individual_page(item)
            except detail.NotAZipFile:
                print("Non-zip file {} encountered. Skipping.".format(item['title']))


def download_videos(jsonfile):
    for i in download_category('Video', jsonfile):
        yield i

def download_audios(jsonfile):
    for i in download_category('Audio', jsonfile):
        yield i
       
def download_docs(jsonfile):
    for i in download_category("Document", jsonfile, make_unique=True):
        yield i
 
def make_channel():
    mychef = PBSChef()
    args = {'token': os.environ['KOLIBRI_STUDIO_TOKEN'], 'reset': True, 'verbose': True}
    options = {}
    mychef.run(args, options)

make_channel()
