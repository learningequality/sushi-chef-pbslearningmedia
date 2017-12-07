import requests
from bs4 import BeautifulSoup
from collections import OrderedDict
from urllib.parse import urljoin
import requests_cache
import scraperwiki

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

def search_index():
    
    for page in range(1, 5000):
        print (page)
        r = requests.get(BASE_URL, params={"q":"*", "page": page})
        r.raise_for_status() # crash out when done
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
            records.append(record)
            
        scraperwiki.sqlite.save(table_name="index", data=record, unique_keys=['link'])

def index_collection(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html5lib")
    container = soup.find("ul", {'id': 'topics-container'})
    topics = container.findAll("li", {'class':'topics-item'}) # <a> tag within
    for topic in topics:
        a = topic.find('a')
        print ('top-item' in topic.attrs['class'], a.text.strip(), a.attrs['href'])
    
index_collection("https://ca.pbslearningmedia.org/collection/montana-shakespeare/")
exit()
        
if __name__ == "__main__":
    search_index()