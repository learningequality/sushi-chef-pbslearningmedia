
demo = "https://ca.pbslearningmedia.org/collection/video-production-behind-the-scenes-with-the-pros/#.WmdDyd-YHCI"
demo2 = "https://ca.pbslearningmedia.org/collection/interview-techniques"

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
requests_cache.install_cache()

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
        self.text = None
        self.url = None
        self.resources = []
        self.category_links = []
        self.categories = []

    def __repr__(self):
        if self.categories:
            return "<{}: {} ({})>".format(self.title, self.categories, len(self.resources))
        else:
            return "<{}: ({})>".format(self.title, len(self.resources))

def crawl_collection(url):
    collection = crawl_category(url)
    for category_name, category_url in collection.category_links:
        category = crawl_category(category_url)
        if category.resources:
            collection.categories.append(category)
    return collection

def crawl_category(url):
    category = Category()
    category.url = url
    response = requests.get(url)
    response.raise_for_status()
    with open("out.html", "wb") as f:
        f.write(response.content)
    soup = BeautifulSoup(response.content, "html5lib")
    make_links_absolute(soup, url)
    category.title = soup.find("h2", {'class': 'coll-title'}).text.strip()
    texts = soup.find("div", {'id': 'coll-default-text'}).find_all("p")
    category.text = '\n'.join([t.text.strip() for t in texts])
    raw_index = soup.find("ul", {'class': 'js-open'}).find_all("li", {"class": 'topics-item'})
    list_index = [i.find("a") for i in raw_index]
    index = [(i.text.strip(), i.attrs['href']) for i in list_index]
    category.category_links = index  # only really relevant for collections!

    # individual items
    # notes: at least some first pages don't have any videos!
    
    raw_items = soup.find("ul", {"class": "coll-items"})
    if raw_items is not None:
        lis = raw_items.find_all("li")
    else:
        lis = []
    for li in lis:
        link = li.find("h2").find("a").attrs['href']
        if link not in crawl_dict:
            print ("{} not crawled".format(link))
            continue # skip
        # item_data['title'] = li.find("h2").find("a").text
        # descr = li.find("div", {"class": 'long-description'}).find_all("p")
        # item_data['description'] = '\n'.join([t.text.strip() for t in descr])
        category.resources.append(crawl_dict[link])
    return category




print (crawl_collection(demo))
#crawl_category(demo2)
