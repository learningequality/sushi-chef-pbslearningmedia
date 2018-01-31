#!/usr/bin/env python
import os
import sys
sys.path.append(os.getcwd()) # Handle relative imports
import requests
from le_utils.constants import licenses
from ricecooker.classes.nodes import DocumentNode, VideoNode, AudioNode, TopicNode
from ricecooker.classes.files import HTMLZipFile, VideoFile, SubtitleFile, DownloadFile, AudioFile, DocumentFile
from ricecooker.chefs import SushiChef
import logging
import detail
import json 
import collection
import string
LOGGER = logging.getLogger()


class PBSChef(SushiChef):
    channel_info = {
        'CHANNEL_SOURCE_DOMAIN': 'dragon.invalid', # who is providing the content (e.g. learningequality.org)
        'CHANNEL_SOURCE_ID': 'dragontest',         # channel's unique id
        'CHANNEL_TITLE': 'Dragon Test',
        'CHANNEL_LANGUAGE': 'en',                          # Use language codes from le_utils
        # 'CHANNEL_THUMBNAIL': 'https://im.openupresources.org/assets/im-logo.svg', # (optional) local path or url to image file
        'CHANNEL_DESCRIPTION': 'Dragon\'s test channel',  # (optional) description of the channel (optional)
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

        #def document_node(document, data, license_type):
        #    print (data['title'])
        #    if document.get_filename().lower().endswith(".pdf"):
        #        node = DocumentNode
        #    else:
        #        node = DownloadNode
        #    assert str == type(data['link'])
        #    return node(source_id=data['link'],
        #                title=data['title'],
        #                description=data['full_description'], # TODO: see below
        #                license = license_type,
        #                copyright_holder="PBS Learning Media",
        #                files = [document,])


        def video_node(video, subtitle, data, license_type):
            if subtitle:
                files = [video, subtitle]
            else:
                files = [video,]
            print (data['title'])
            assert str== type(data['link'])
            return VideoNode(source_id=data['link'],
                             title=data['title'],
                             description=data['full_description'],  # TODO: get full descriptiom
                             license=license_type, 
                             copyright_holder="PBS Learning Media",
                             files=files,
                             )            
        
        def handle_collection(url):
            # TODO - handle zero length collections
            # TODO - handle collections with top level resources
            node_function = {#DocumentFile: document_node,
                             AudioFile: audio_node,
                             }
            collection_contains_data = False

            coll_struct = collection.crawl_collection(url)
            assert type(coll_struct.url) == str
            topic_node = TopicNode(source_id=coll_struct.url,
                                   title=coll_struct.title, # coll_struct.title,
                                   description=coll_struct.description,) #coll_struct.description)
            for category in coll_struct.categories:
                category_contains_data = False
                assert type(category.url) == str
                category_node = TopicNode(source_id=category.url,
                                          title=category.title, #category.title ,
                                          description=category.description, )#category.description)
                print(category)
                for resource in category.resources:
                     print(resource)
                     try:
                        res, data = detail.get_individual_page(resource)
                     except Exception:
                        continue
                     collection_contains_data = True
                     category_contains_data = True
                     if type(res) in [AudioFile, DocumentFile]:
                         print(type(res))
                         resource_node = node_function[type(res)](res, data, licenses.CC_BY_NC_ND) # TOOD FIX LICENCE!
                     else:
                         print ("video")
                         resource_node = video_node(res[0], res[1], data, licenses.CC_BY_NC_ND) # TODO FIX LICENCE!
                     category_node.add_child(resource_node)
                if category_contains_data:
                    topic_node.add_child(category_node)
                else:
                    print ("No content in category {}".format(resource))
            if collection_contains_data:
                return topic_node
            else:
                print ("No content in collection {}".format(url))
                return None
             
            
            

    
        # create channel
        channel = self.get_channel(**kwargs)
        
        #collection_node = handle_collection("https://ca.pbslearningmedia.org/collection/interview-techniques")
        for collection_url in all_collections():
            collection_node = handle_collection(collection_url)
            if collection_node is not None:
                channel.add_child(collection_node)
        # create a topic and add it to channel
        data = {}
        
#        for doc, data in download_docs("share.json"):
#            channel.add_child(document_node(doc, data, licenses.CC_BY_NC_ND)) # was _SA
       # for audio, data in download_audios("share.json"):
       #     channel.add_child(audio_node(audio, data, licenses.CC_BY_NC_ND)) # was _SA
       # for (video, subtitle), data in download_videos("share.json"):
       #     channel.add_child(video_node(video, subtitle, data, licenses.CC_BY_NC_ND)) # was _SA
        return channel




def all_collections():
    with open("collection.json") as f:
        lines = set(f.readlines())
    database = [json.loads(line) for line in lines]
    for item in database:
        yield item['link']
    
   
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
            except NotImplementedError:
                pass


def download_videos(jsonfile):
    for i in download_category('Video', jsonfile):
        yield i

def download_audios(jsonfile):
    for i in download_category('Audio', jsonfile):
        yield i
       
#def download_docs(jsonfile):
#    for i in download_category("Document", jsonfile, make_unique=True):
#        yield i


 
def make_channel():
    mychef = PBSChef()
    args = {'token': os.environ['KOLIBRI_STUDIO_TOKEN'], 'reset': True, 'verbose': True}
    options = {}
    mychef.run(args, options)

make_channel()
