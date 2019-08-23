#!/usr/bin/env python
import os
import sys
sys.path.append(os.getcwd()) # Handle relative imports
import requests
from le_utils.constants import licenses
from ricecooker.classes.nodes import DocumentNode, VideoNode, AudioNode, TopicNode, Node
from ricecooker.classes.files import HTMLZipFile, VideoFile, SubtitleFile, DownloadFile
from ricecooker.chefs import SushiChef
from ricecooker.classes.licenses import SpecialPermissionsLicense
import logging
import jsonlines
import tags
import add_file
import download

sys.setrecursionlimit(10000)
LOGGER = logging.getLogger()
MAX_NODE_LENGTH = 500

SHARE_LICENCE = SpecialPermissionsLicense(copyright_holder="PBS", description='Verbatim Use ("Stream, Download, and Share") — You are permitted to download the Content, make verbatim copies of the Content, incorporate the Content unmodified into a presentation, and distribute verbatim copies of the Content, but you may not edit or alter the Content or create any derivative works of the Content. You must attribute the Content as indicated in the Download Package.')

MODIFY_LICENCE = SpecialPermissionsLicense(copyright_holder='PBS', description='Download to Re-edit and Distribute ("Stream, Download, Share, and Modify") — You are permitted to download, edit, distribute, and make derivative works of the Content. You must attribute the Content as indicated in the Download Package. Read the full license.')

licence_lookup = {"Stream, Download and Share": SHARE_LICENCE,
                  "Stream, Download, Share, and Modify": MODIFY_LICENCE}

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

nodes = {}
def hier(medium, curriculum_tags):
    out_tags = []
    all_ancestors = []
    for tag in curriculum_tags:
        all_ancestors.extend(tag['ancestor_ids'])
    retry = {}
    for tag in sorted(curriculum_tags, key =lambda x: x['id']):
        slug = tag['slug']
        _id = tag['id']
        name = tag['name']
        if not tag['ancestor_ids']:
            ancestor = "ROOT"
        else:
            ancestor = tag['ancestor_ids'][-1]
        # attach to tree
        if _id not in nodes[medium]:
            nodes[medium][_id] = TopicNode(source_id=slug, title =name)
            try:
                nodes[medium][ancestor].add_child(nodes[medium][_id])
            except Exception:
                retry[(medium,ancestor)] = nodes[medium][_id]      
        if _id not in all_ancestors:
            out_tags.append(nodes[medium][_id])
    for k,v in retry.items():
        nodes[k[0]][k[1]].add_child(v)
    assert out_tags
    return out_tags
  

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
        i=0
        for medium in leaf_tags: # 'Audio'
            if medium != "Video": continue
            nodes[medium]={}
            nodes[medium]["ROOT"] = TopicNode(source_id = medium, title = medium)
            channel.add_child(nodes[medium]["ROOT"])
            for i, index in enumerate(index_data):

                if i<6710: continue
               
                leafs = hier(medium, index['detail']['curriculum_tags'])
                resource_url = index['detail']['objects'][0]['canonical_url']
                print ("#", i, ":", resource_url)
                #for x in index['detail']['objects']:
                #    print (x['canonical_url'], x['role'])
                  
                canonical = index['index']['canonical_url']
                assert canonical is not None


                try:
                    nodes[canonical], _ = download.download_video_from_html(canonical_url=resource_url,
                                                           title=index['index']['title'],
                                                           license=licence_lookup[index['detail']['use_rights']],
                                                           copyright_holder="PBS Learning Media",
                                                           description=index['detail']['description']                
                                         )
                except download.NotAVideo:
                    with open("fail.log", "a") as f:
                        f.write(str(i)+":"+canonical + " isn't a video\n")
                    continue
                except add_file.CantMakeNode:
                    with open("fail.log", "a") as f:
                        f.write(str(i)+":"+canonical + " is a bad video\n")
                    continue
               

                for leaf in leafs:
                    # print (leaf)
                    leaf.add_child(nodes[canonical])             

        return channel
 
def make_channel():
    mychef = PBS_API_Chef()
    #args = {'token': os.environ['KOLIBRI_STUDIO_TOKEN'], 'reset': True, 'verbose': True}
    #options = {}
    #mychef.run(args, options)
    mychef.main()

make_channel()
