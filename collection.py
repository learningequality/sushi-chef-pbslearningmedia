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

import requests
from bs4 import BeautifulSoup
import json

def crawl(url):
    response = requests.get(url)
    response.raise_for_status()
    with open("out.html", "wb") as f:
        f.write(response.content)
    soup = BeautifulSoup(response.content, "html5lib")
    title = soup.find("h2", {'class': 'coll-title'}).text.strip()
    texts = soup.find("div", {'id': 'coll-default-text'}).find_all("p")
    text = '\n'.join([t.text.strip() for t in texts])
    raw_index = soup.find("ul", {'class': 'js-open'}).find_all("li", {"class": 'topics-item'})
    list_index = [i.find("a") for i in raw_index]
    index = [(i.text.strip(), i.attrs['href']) for i in list_index]
    # .attrs['href']
    # .text
    print (title, text, index)

    # individual items
    print ("###")

    # THE REASON WHY THIS ISN'T WORKING IS BECAUSE THE FIRST PAGE HAS NO VIDEOS!


    raw_items = soup.find("ul", {"class": "coll-items"}).find_all("li")
    item_data = {}
    for li in raw_items:
        item_data['title'] = li.find("h2").find("a").text
        item_data['link'] = li.find("h2").find("a").attrs['href']
        descr = li.find("div", {"class": 'long-description'}).find_all("p")
        item_data['description'] = '\n'.join([t.text.strip() for t in descr])
        print (item_data)
         
        

crawl(demo2)
