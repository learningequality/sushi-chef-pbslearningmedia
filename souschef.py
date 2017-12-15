#!/usr/bin/env python
import os
import sys
sys.path.append(os.getcwd()) # Handle relative imports
import requests
from le_utils.constants import licenses
from ricecooker.classes.nodes import DocumentNode, VideoNode
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
        def video_node(video, subtitle, data):
            if subtitle:
                files = [video, subtitle]
            else:
                files = [video]
            return VideoNode(source_id=data['link'],
                             title=data['link'],
                             license=licenses.CC_BY_NC_SA, 
                             copyright_holder="PBS Learning Media",
                             files=files,
                             )            
            
        # create channel
        channel = self.get_channel(**kwargs)
        # create a topic and add it to channel
        data = {}
        
        
        for (video, subtitle), data in download_videos("share.json"):
            channel.add_child(video_node(video, subtitle, data))
        return channel
    
def download_videos(jsonfile):
    with open(jsonfile) as f:
        database = [json.loads(line) for line in f.readlines()]
        
    i = 0
    for item in database:
        if item['category'] in ["Video"]: # ("Document", "Audio", "Image", "Video"):
            yield detail.get_individual_page(item)
            i=i+1
            if i == 4:
                print ("Artificial quit")
                break
        
def make_channel():
    mychef = PBSChef()
    args = {'token': os.environ['KOLIBRI_STUDIO_TOKEN'], 'reset': False, 'verbose': True}
    options = {}
    mychef.run(args, options)

make_channel()
