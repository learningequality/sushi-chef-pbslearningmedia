import requests
from bs4 import BeautifulSoup
from collections import OrderedDict
from urllib.parse import urljoin
import requests_cache
import json
import re

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

        if page == 1:
            print (r.url)
            print (soup.find("div", {'class': 'search-summary-text'}).text)

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

def top_level_subject_ids():
    url = "https://www.pbslearningmedia.org/search/?q=&selected_facets="
    response = requests.get(url)
    items = BeautifulSoup(response.text, "html5lib").findAll("a", {"class": "facet-name "})
    urls = [x.attrs['href'] for x in items]
    catnames = [x.text.strip() for x in items]
    output = []
    for url, cat in zip(urls, catnames):
        node = re.search("%3A(\d+)&", url).groups()[0]
        output.append([cat, node])
    return output

def mid_level_subject_ids(_id=2663):
    url = "https://www.pbslearningmedia.org/search/?q=&selected_facets=supplemental_curriculum_hierarchy_nodes%3A{}&selected_facets=".format(_id)
    response = requests.get(url)
    div = BeautifulSoup(response.text, "html5lib").find("div", {"id": "facet-subject-{}-facet-container".format(_id)})
    #div = BeautifulSoup(response.text, "html5lib").find("ul", {"class":"no-list-style std-wb"})
    items = div.findAll("a", {"class": "facet-name "})
    urls = [x.attrs['href'] for x in items]
    catnames = [x.text.strip() for x in items]
    output = []
    for url, cat in zip(urls, catnames):
        node = re.search("%3A(\d+)&", url).groups()[0]
        output.append([cat, node])
    return output

def build_subject_index():
    top_level = top_level_subject_ids()
    hierarchy = {}
    for (name, _id) in top_level:
        print (name, _id)
        mid_level = (mid_level_subject_ids(_id))
        hierarchy[_id] = (name, mid_level)
        for (name, _id) in mid_level:
            print(name, _id)
            #https://www.pbslearningmedia.org/search/?q=&selected_facets=supplemental_curriculum_hierarchy_nodes%3A1185&page=2
            save_index({"q": "",
                        "selected_facets": "supplemental_curriculum_hierarchy_nodes:{}".format(_id)}, "cat_{}.json".format(_id))

    with open("hierarchy.json", "w") as f:
        json.dump(hierarchy, f)

def build_reverse_index():
    """run build_subject_index() first
       take cat_xxxx and hierarchy json files and generate list of URL ->
       category mappings."""

    class SetEncoder(json.JSONEncoder):
        # https://stackoverflow.com/questions/8230315/how-to-json-serialize-sets/8230505#8230505
        def default(self, obj):
            if isinstance(obj, set):
                return list(obj)
            return json.JSONEncoder.default(self, obj)


    with open("hierarchy.json") as f:
        hierarchy = json.load(f)
    data = {}
    for top_id in hierarchy.keys():
        top_name, mid_level = hierarchy[top_id]
        for mid_name, mid_id in mid_level:
            print (mid_name)
            with open("cat_{}.json".format(mid_id)) as f:
                for line in f.readlines():
                    j = json.loads(line)
                    link = j['link']
                    if link not in data:
                        data[link] = set()
                    data[link].add((top_name, mid_name))

    with open("reverse.json", "w") as f:
        json.dump(data, f, cls=SetEncoder)



#//div[@id='supplemental_curriculum_hierarchy_nodes-facet-container']//a[@class='facet-name']



if __name__ == "__main__":
    #build_subject_index()
    #build_reverse_index()

    #exit()
    save_index({"selected_facets":"permitted_use_exact:Stream, Download, Share, and Modify"}, "modify.json")
    #save_index({"q": "kitten"}, "kitten.json")
    save_index({"selected_facets":"media_type_exact:Collection"}, "collection.json")
    save_index({"selected_facets":"permitted_use_exact:Stream, Download and Share"}, "share.json")
    #save_index({"selected_facets":"permitted_use_exact:Stream and Download"}, "download.json")
    #search_index({"selected_facets":"permitted_use_exact:Stream Only"}, "stream.json")

