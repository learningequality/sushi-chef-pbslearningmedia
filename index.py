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

def search_index(params=None, flags=None):
    # params: search parameters to add
    # flags: flags to set if found: key/value pairs.
    
    if flags is None:
        flags = {}
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
            for flag in flags:
                record[flag] = flags[flag]
            records.append(record)
        for record in records:
            print (record.get('is_a_kitten'))
            
        scraperwiki.sqlite.save(table_name="index", data=records, unique_keys=['link'])

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
    #search_index()
    #search_index({"selected_facets":"permitted_use_exact:Stream, Download, Share, and Modify"}, {"modify": True})
    search_index({"q": "kitten"}, {"is_a_kitten": True})
    #search_index({"selected_facets":"permitted_use_exact:Stream, Download and Share"}, {"share": True})
    #search_index({"selected_facets":"permitted_use_exact:Stream and Download"}, {"download": True})
    #search_index({"selected_facets":"permitted_use_exact:Stream Only"}, {"stream": True}) 
        