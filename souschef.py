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
import detail
import json 

LOGGER = logging.getLogger()

## this is just a bit of debug code: TODO delete this
## NOPE: now actively ignoring duplicates!
def add_child_placeholder(self, node):
    if node in self.children:
        raise RuntimeError("double node")
        return
    assert isinstance(node, Node)
    node.parent = self
    self.children += [node]

Node.add_child = add_child_placeholder
######


class PBSChef(SushiChef):
    # hierarchy = # open reverse.json and parse
    
    channel_info = {
        'CHANNEL_SOURCE_DOMAIN': 'pbslearningmedia.org', # who is providing the content (e.g. learningequality.org)
        'CHANNEL_SOURCE_ID': 'dragon__pbslearningmedia',         # channel's unique id
        'CHANNEL_TITLE': 'PBS Learning Media',
        'CHANNEL_LANGUAGE': 'en',                          # Use language codes from le_utils
        # 'CHANNEL_THUMBNAIL': 'https://im.openupresources.org/assets/im-logo.svg', # (optional) local path or url to image file
        'CHANNEL_DESCRIPTION': 'Bring Your Classroom to Life With PBS',  # (optional) description of the channel (optional)
    }

    def construct_channel(self, **kwargs):
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
        
        def handle_resource_node(resource_node):
            # handle hierarchy
            categories = reverse_lookup.get(data['link'], [])
            for cat in categories:
                cat_nodes[tuple(cat)].add_child(resource_node) # contains implicit assertion that contents exist

            # handle collections
            collections = coll_reverse_lookup.get(data['link'], [])
            for coll in collections:
                coll_nodes[tuple(coll)].add_child(resource_node) 
        
            # handle alphabet
            letter = first_letter(data['title'])
            letters[letter].add_child(resource_node) # was _SA        
                
        
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
        

    
        # create channel
        channel = self.get_channel(**kwargs)
        letters = {}
        alphabetical_index = TopicNode(source_id="alphabetical",
                                       title="Alphabetical Index",
                                       description="All resources, by initial letter")
        channel.add_child(alphabetical_index)
        for letter in "#ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            letters[letter] = TopicNode(source_id="letter-"+letter,
                                        title=letter, # coll_struct.title,
                                        description="Resources starting with "+ letter)
            alphabetical_index.add_child(letters[letter])

        
        category_index = TopicNode(source_id="category",
                                   title = "Categorical Index",
                                   description="")
        cat_nodes = {}
        coll_nodes = {}
        channel.add_child(category_index)
        with open("reverse.json") as f:
            reverse_lookup = json.load(f)
        with open("hierarchy.json") as f:
            hierarchy = json.load(f)

        with open("collection_reverse.json") as f:
            coll_reverse_lookup = json.load(f)
        with open("collection_hierarchy.json") as f:
            coll_hierarchy = json.load(f)

        def create_hierarchy(hierarchy, name, node_structure):
            for top_level in hierarchy:
                top_name, sub_level = hierarchy[top_level]
                top_node = TopicNode(source_id="{}_{}".format(name, top_level),
                                     title=top_name)
                category_index.add_child(top_node)
                for sub_item in sub_level:
                    sub_name, sub_id = sub_item
                    sub_node = TopicNode(source_id="{}_{}".format(name, sub_id),
                                         title=sub_name)
                    top_node.add_child(sub_node)
                    node_structure[(top_name, sub_name)] = sub_node
                
        create_hierarchy(hierarchy, "cat", cat_nodes)
        create_hierarchy(coll_hierarchy, "coll", coll_nodes)
            
        # create a topic and add it to channel
        data = {}
        
#        for doc, data in download_docs("share.json"):
#            channel.add_child(document_node(doc, data, licenses.CC_BY_NC_ND)) # was _SA
        i = 0
        for audio, data in download_audios("share.json"):
            # this is the only bit that's audio specific, refactor out all the other junk
            resource_node = audio_node(audio, data, licenses.CC_BY_NC_ND)
            handle_resource_node(resource_node)
            #### handle hierarchy
            ###categories = reverse_lookup.get(data['link'], [])
            ###print (categories)
            ###for cat in categories:
            ###    cat_nodes[tuple(cat)].add_child(resource_node) # contains implicit assertion that contents exist
            ###
            #### handle collections
            ###collections = coll_reverse_lookup.get(data['link'], [])
            ###for coll in collections:
            ###   coll_nodes[tuple(coll)].add_child(resource_node) # contains implicit assertion that contents exist
            #### handle alphabet
            ###letter = first_letter(data['title'])
            ###letters[letter].add_child(resource_node) # was _SA
            #handle skip: delete this!
            #i=i+1
            #if i>3: break
        #for (video, subtitle), data in download_videos("share.json"):
        #    letter = first_letter(data['title'])
        #    letters[letter].add_child(video_node(video, subtitle, data, licenses.CC_BY_NC_ND)) # was _SA
        #for audio, data in download_audios("modify.json"):
        #    letter = first_letter(data['title'])
        #    letters[letter].add_child(audio_node(audio, data, licenses.CC_BY_NC_ND)) # was _SA
        #for (video, subtitle), data in download_videos("modify.json"):
        #    letter = first_letter(data['title'])
        #    letters[letter].add_child(video_node(video, subtitle, data, licenses.CC_BY_NC_ND)) # was _SA
        return channel

    
def download_category(category, jsonfile, make_unique=True):
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
#    for i in download_category("Document", jsonfile):
#        yield i
 
def make_channel():
    mychef = PBSChef()
    args = {'token': os.environ['KOLIBRI_STUDIO_TOKEN'], 'reset': True, 'verbose': True}
    options = {}
    mychef.run(args, options)

make_channel()
