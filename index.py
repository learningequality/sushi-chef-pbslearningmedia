import requests
from bs4 import BeautifulSoup
from collections import OrderedDict
from urllib.parse import urljoin
import requests_cache
import json

requests_cache.install_cache()

BASE_URL = "https://ca.pbslearningmedia.org/search/"

def get_text(tag):
    # tag can be None
    if tag is None:
        return ""
    else:
        return tag.text.strip()
    
def full_url(link):
    # don't join if no link
    if not link:
        return ""
    return urljoin(BASE_URL, link)

def search_index(params=None):
    # params: search parameters to add
    
    if params is None:
        params = {"q": "*"}
    elif "q" not in params.keys():
        params['q'] = "*"
        
    for page in range(1, 5000):
        print (page)
        params['page'] = page
        r = requests.get(BASE_URL, params=params)
        try:
            r.raise_for_status() # crash out when done
        except:
            break
        soup = BeautifulSoup(r.content, "html5lib")
        
        items = soup.findAll("div", {"class":"search-item"})
        records = []
        for item in items:
            record = {}
            record['title'] = get_text(item.find("h3"))
            record['description'] = get_text(item.find("div", {'class': 'search-info-description'}))
            record['category'] = item.find("span", {'class': 'info-container icon-tooltip'}).attrs.get("data-title").strip()
            record['grades'] = get_text(item.find("span", {'class': 'info-container grades-tooltip'}))
            record['brand'] = get_text(item.find("span", {'class': 'brand-tooltip'}))
            img = item.find("div", {'class': 'search-item-figure'})
            record['thumbnail'] = full_url(img.find("img").attrs.get("src"))
            record['link'] = full_url(img.find("a").attrs.get("href"))
            record['runtime'] = get_text(item.find("span", {'class': 'search-info-duration'}))
            yield record

def save_index(q, file):
    with open(file, "w") as f:
        for i, record in enumerate(search_index(q)):
            if i>0: f.write("\n")
            f.write(json.dumps(record))

def index_collection(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html5lib")
    container = soup.find("ul", {'id': 'topics-container'})
    topics = container.findAll("li", {'class':'topics-item'}) # <a> tag within
    for topic in topics:
        a = topic.find('a')
        print ('top-item' in topic.attrs['class'], a.text.strip(), a.attrs['href'])
    
#index_collection("https://ca.pbslearningmedia.org/collection/montana-shakespeare/")
#exit()
        
if __name__ == "__main__":
    #save_index({"selected_facets":"permitted_use_exact:Stream, Download, Share, and Modify"}, "modify.json")
    #save_index({"q": "kitten"}, "kitten.json")
    save_index({"selected_facets":"media_type_exact:Collection"}, "collection.json")
    #save_index({"selected_facets":"permitted_use_exact:Stream, Download and Share"}, "share.json")
    #save_index({"selected_facets":"permitted_use_exact:Stream and Download"}, "download.json")
    #search_index({"selected_facets":"permitted_use_exact:Stream Only"}, "stream.json") 
        
