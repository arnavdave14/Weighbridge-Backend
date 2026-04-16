import requests
from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.getcwd())
from app.config.settings import settings

PORTAL_USER = settings.DIGITALSMS_PORTAL_USER
PORTAL_PASS = settings.DIGITALSMS_PORTAL_PASS
BASE_URL = "https://api.digitalsms.net"

def fetch_api_docs():
    session = requests.Session()
    session.post(f"{BASE_URL}/login", data={"username": PORTAL_USER, "password": PORTAL_PASS})
    
    url = f"{BASE_URL}/w/sendingapi.jsp"
    resp = session.get(url)
    
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Dump exactly what is inside the main container
        main_content = soup.find("div", class_="nk-content-body")
        if main_content:
            print(main_content.get_text(separator="\n", strip=True))
        else:
            print(soup.get_text(separator="\n", strip=True))
            
if __name__ == "__main__":
    fetch_api_docs()
