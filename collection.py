
demo = "https://ca.pbslearningmedia.org/collection/video-production-behind-the-scenes-with-the-pros/#.WmdDyd-YHCI"
demo2 = "https://ca.pbslearningmedia.org/collection/interview-techniques"
demo_nested = "https://ca.pbslearningmedia.org/collection/montana-shakespeare/"

"""
//div[@id='coll-default-text']//p  - top level text (same xpath for root and sub items but different text)
//li[@class='topics-item top-item']/a/@href - links to sub items (same data for root and sub items)

-- individual items lack some info -- but we can look that up in the json files!
//ul[@class='coll-items no-list-style']/li -- individual item tag
...//h2/a -- header
...//div[@class='long-description']/p -- body text
"""

import urllib.parse
import requests
from bs4 import BeautifulSoup
import json
import re
import requests_cache
import string
import hashlib
from ricecooker.classes.nodes import TopicNode

requests_cache.install_cache()

def sha1(source):
    return hashlib.sha1(source.encode('utf-8')).hexdigest()

def make_links_absolute(soup, url):
    # https://stackoverflow.com/questions/4468410/python-beautifulsoup-equivalent-to-lxml-make-links-absolute
    for tag in soup.findAll('a', href=True):
        tag['href'] = urllib.parse.urljoin(url, tag['href'])

crawl = []

with open("modify.json") as f:
     crawl.extend(list(json.loads(x) for x in f.readlines()))
with open("share.json") as f:
     crawl.extend(list(json.loads(x) for x in f.readlines()))

# the JSON file has additional path elements:
# /resource/<resource_id>/<nice_name>/
# as opposed to the crawl
# /resource/<resource_id>/
# <nice_name> is optional and entirely replaceable with, e.g. "kitten" and still works.
# therefore our key needs to be everything before the slash after resource/.../
crawl_dict = {}
for item in crawl:
    shortname = re.search(r"(.*resource\/[^\/]*\/)", item['link']).group(0)
    crawl_dict[shortname] = item
    
class Category(object):
    def __init__(self):
        self.title = None
        self.description = None
        self.url = None
        self.resources = []
        self.category_links = []
        self.categories = []
        
    def populated(self):
        if bool(self.resources):
            return True
        if any(x.populated() for x in self.categories):
            return True
        return False
    
    def empty(self):
        return not self.populated()
        
    def __repr__(self):
        if self.categories:
            return "<{}: {} ({})>".format(self.title, self.categories, len(self.resources))
        else:
            return "<{}: ({})>".format(self.title, len(self.resources))
        
    def depth(self):
        while True:
            if not(self.categories):
                return 1
            return max(x.depth() for x in self.categories)+1

def crawl_collection(url):
    collection = crawl_category(url)
    for category_name, category_url in collection.category_links:
        category = crawl_category(category_url)
        if category.resources:
            collection.categories.append(category)
    return collection

def crawl_category(url):
    # TODO pagination: https://ca.pbslearningmedia.org/collection/idptv/ -> /idptv/2
    # next page is contained in //li[@class='coll-next']/a/@href
    #print ('Category', url)
    assert type(url) == str, type(url)
    category = Category()
    category.url = url
    response = requests.get(url)
    try:
        response.raise_for_status()
    except Exception:
        return category
    #with open("out.html", "wb") as f:
    #    f.write(response.content)
    soup = BeautifulSoup(response.content, "html5lib")
    make_links_absolute(soup, url)
    category.title = soup.find("h2", {'class': 'coll-title'}).text.strip()
    try:
        texts = soup.find("div", {'id': 'coll-default-text'}).find_all("p")
        category.description = '\n'.join([t.text.strip() for t in texts])
    except AttributeError:
        category.description = ""
    try:
        raw_index = soup.find("ul", {'class': 'js-open'}).find_all("li", {"class": 'topics-item'})
        # also check for subtopic or top-item in same to get top 
    except AttributeError:
        raw_index = []
    # also check for subtopic or top-item in same li's class to get supercategories
    
    list_index = [i.find("a") for i in raw_index]
    #top_level_index = ["*" if "top-item" in i.attrs['class'] else " " for i in raw_index] 
    top_level_index = ["" for i in raw_index]  # USE LINE ABOVE IF YOU WANT TO THINK ABOUT NESTING
    
    try:
        index = [(j + i.text.strip(), i.attrs['href']) for i,j in zip(list_index, top_level_index)]
    except AttributeError:
        index = []
    category.category_links = index  # only really relevant for collections!

    # individual items
    # notes: at least some first pages don't have any videos!
    
    raw_items = soup.find("ul", {"class": "coll-items"})
    if raw_items is not None:
        lis = raw_items.find_all("li")
    else:
        lis = []
    for li in lis:
        try:
            link = li.find("h2").find("a").attrs['href']
        except Exception:
            continue # rare issue found on https://ca.pbslearningmedia.org/collection/new-to-learningmedia/
        if link not in crawl_dict:
            #print ("{} not crawled".format(link))
            continue # skip
        item_data = dict(crawl_dict[link])
        item_data['title'] = crawl_dict[link]['title']
        item_data['full_description'] = crawl_dict[link]['description']
        #item_data['title'] = li.find("h2").find("a").text
        #descr = li.find("div", {"class": 'long-description'}).find_all("p")
        #item_data['description'] = '\n'.join([t.text.strip() for t in descr])
        
        category.resources.append(item_data)
    return category


def all_collections():
    
    reverse = {}
    hierarchy = {}
    
    with open("collection.json") as f:
        for line in f.readlines():
            url = json.loads(line)['link']
            top_collection = crawl_collection(url)
            if top_collection.empty():
                print ("EMPTY: ", top_collection)
                continue
            print (top_collection)
            categories = top_collection.categories
            hierarchy_list = []
            for cat in categories:
                hierarchy_list.append([cat.title, sha1(cat.url)])
                for resource in cat.resources:
                    link = resource['link']
                    if link not in reverse:
                        reverse[link] = []
                    reverse[link].append([top_collection.title, cat.title])
            hierarchy[sha1(top_collection.url)] = [top_collection.title, hierarchy_list]
            
    
    with open("collection_hierarchy.json", "w") as f:
        json.dump(hierarchy, f)
    with open("collection_reverse.json", "w") as f:
        json.dump(reverse, f)
                
    
            #{"top_id": ["topname", [["catname", "cat_id"], ["catname", "cat_id"]], "top_id": ... hierarchy.json
            #+
            #{"url": [["The Arts", "Visual Art"], ["Cats", "Dogs"]], "url": ... reverse.json
                        
            
            
            
            



all_collections()
#collection = crawl_collection(demo)
#print (collection.depth())
#print()
#q=crawl_category(demo_nested)
exit()
