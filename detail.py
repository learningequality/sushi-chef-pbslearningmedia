import login
from urllib.parse import urljoin
from bs4 import BeautifulSoup
session = login.session

sample_url="https://ca.pbslearningmedia.org/resource/vtl07.la.rv.text.cats/cats/"

def get_video_page(url, get_video=True):
    # works for audio, individual images, 
    # downloading appears broken on website for "media gallery" (in images, documents...)
    # interactive things appear broken on website in entirety (and no download link)
    # webpages are just external links (many broken)
    # self-guided lessons - download broken, looks complex
    # lesson plan -- appears to not be its own thing, mostly. At least one is v. lon
    
    
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html5lib")
    # TODO -- turn this into something useful.
    print (soup.find("div", {'class': 'resource-content'}))
    
    if get_video:
        print ("Downloading zip...")
        form = soup.find("form", {"id": "download_form"})
        target = urljoin(url, form.attrs['action'])
    
        # Note: redirection URL valid only for an hour or so.
        zip_response = session.post(target, data={"agree": "on"})
        with open("sample.zip", "wb") as f:
            f.write(zip_response.content)
            
        print ("{} bytes written".format(len(zip_response.content)))

    


login.login()
#get_video_page(sample_url, get_video=False)
get_video_page("https://ca.pbslearningmedia.org/resource/watsol.sci.ess.water.bfdq/bernheim-forest-discussion-questions/")