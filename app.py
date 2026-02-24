import re
import requests
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = FastAPI()

def normalize_domain(url):

    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)

    return parsed.netloc.replace("www.","")


def find_social(domain):

    headers = {
        "User-Agent":"Mozilla/5.0"
    }

    facebook=[]
    line=[]

    try:

        r=requests.get("https://"+domain,headers=headers,timeout=10)

        soup=BeautifulSoup(r.text,"html.parser")

        for a in soup.find_all("a"):

            href=a.get("href","")

            if "facebook.com" in href:
                facebook.append(href)

            if "line.me" in href or "lin.ee" in href:
                line.append(href)

    except:
        pass

    return facebook,line


@app.get("/",response_class=HTMLResponse)
def home():

    return """

<h2>Brand Bot</h2>

輸入網址：

<form method="post" action="/analyze">

<input name="url" style="width:300px">

<button>搜尋</button>

</form>

"""


@app.post("/analyze",response_class=HTMLResponse)
@app.post("/analyze", response_class=HTMLResponse)
def analyze(url: str = Form(...)):

    domain = normalize_domain(url)
    facebook, line = find_social(domain)

    return f"""
<h2>Brand Bot 結果</h2>

Domain:
{domain}

<br><br>

Facebook:
{facebook}

<br><br>

LINE:
{line}

<br><br>

<a href="/">再查一個</a>

"""
