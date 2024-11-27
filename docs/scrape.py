import json
import os
import requests
from bs4 import BeautifulSoup

# First we get links from the base page
# https://slurm.schedmd.com/documentation.html
# But we are going to ignore Publications / Presentations

here = os.path.dirname(os.path.abspath(__file__))

# Create pages output directory
outdir = os.path.join(here, "pages")
if not os.path.exists(outdir):
    os.makedirs(outdir)

# Pretend we are a real person...
url_headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "en-US, en;q=0.5",
}

root = "https://slurm.schedmd.com"
base = requests.get(f"{root}/documentation.html", headers=url_headers)
soup = BeautifulSoup(base.content, "html.parser")

links = soup.find_all("li")
urls = set()
for link in links:
    # These are top level wrappers to items below
    link_class = link.get("class")
    if link_class and "site-menu__item" in link_class:
        continue
    # This is the child
    ahref = link.a
    if not ahref:
        print(f"Warning, link has no a element:\n{link}")
        continue
    href = ahref.get("href")
    if not href:
        print(f"Warning, a element has no href attribute:\n{ahref}")
        continue
    # Relative link
    if href.startswith("#"):
        continue
    url = href
    # Skip external links
    if "http" in url and "schedmd.com" not in url:
        continue
    if "schedmd.com" not in url:
        url = f"{root}/{url}"
    print(f"Will parse {url}")
    urls.add(url)

results = []
for url in urls:
    print(f"Retrieving {url}")
    result = {"url": url}
    response = requests.get(url, headers=url_headers)
    if response.status_code != 200:
        raise ValueError(f"Could not get {url}: {response.reason}")
    soup = BeautifulSoup(response.content, "html.parser")

    # Flatten headers into sections
    sections = []
    header_names = ["h1", "h2", "h3"]
    seen = set()
    for header in header_names:
        headers = soup.find_all(header)
        for section in headers:
            if section.text in seen:
                continue
            seen.add(section.text)
            new_section = {"title": section.text}
            content = ""
            for sibling in section.find_next_siblings():
                # This subheader is being added to a parent section
                if sibling.name in header_names:
                    seen.add(sibling.text)
                content += sibling.text
            new_section["content"] = content
            if content:
                sections.append(new_section)
    result["sections"] = sections
    results.append(result)

with open("slurm-docs.json", "w") as fd:
    fd.write(json.dumps(results, indent=4))

# Also break into pages
for result in results:
    if not result["sections"]:
        continue
    slug = os.path.basename(result["url"].rstrip('/')).split(".")[0]
    outfile = os.path.join(outdir, f"{slug}.json")
    with open(outfile, "w") as fd:
        fd.write(json.dumps(result, indent=4))
