from bs4 import BeautifulSoup
import json
import os, sys
import pandas as pd
import re
import requests
import subprocess
from datetime import  datetime, date, timedelta

def text_from_pdf(pdf_path, temp_path):
    if os.path.exists(temp_path):
        os.remove(temp_path)
    subprocess.call(["pdftotext", pdf_path, temp_path])
    f = open(temp_path, encoding="utf8")
    text = f.read()
    f.close()
    os.remove(temp_path)
    return text

base_url  = "http://papers.nips.cc"

index_urls = {1987: "https://papers.nips.cc/book/neural-information-processing-systems-1987"}
for i in range(1, 30):
    year = i+1987
    index_urls[year] = "http://papers.nips.cc/book/advances-in-neural-information-processing-systems-%d-%d" % (i, year)

nips_authors = set()
papers = list()
paper_authors = list()

startime = datetime.now()
for year in sorted(index_urls.keys()):
    index_url = index_urls[year]
    index_html_path = os.path.join("working", "html", str(year)+".html")

    if not os.path.exists(index_html_path):
        r = requests.get(index_url)
        if not os.path.exists(os.path.dirname(index_html_path)):
            os.makedirs(os.path.dirname(index_html_path))
        with open(index_html_path, "wb") as index_html_file:
            index_html_file.write(r.content)
    with open(index_html_path, "rb") as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, "lxml")
    paper_links = [link for link in soup.find_all('a') if link["href"][:7]=="/paper/"]
    print("Year: {}; {} Papers Found; Time Elapsed: {} mins".format(year,len(paper_links),str(int((datetime.now()-startime).seconds/60))))


    temp_path = os.path.join("working", "temp.txt")

    for link in paper_links:
        paper_title = link.contents[0]
        info_link = base_url + link["href"]
        pdf_link = info_link + ".pdf"
        pdf_name = link["href"][7:] + ".pdf"
        pdf_path = os.path.join("working", "pdfs", str(year), pdf_name)
        paper_id = re.findall(r"^(\d+)-", pdf_name)[0]
#         print(year, " ", paper_id) #paper_title.encode('ascii', 'namereplace'))
        if not os.path.exists(pdf_path):
            pdf = requests.get(pdf_link)
            if not os.path.exists(os.path.dirname(pdf_path)):
                os.makedirs(os.path.dirname(pdf_path))
            pdf_file = open(pdf_path, "wb")
            pdf_file.write(pdf.content)
            pdf_file.close()

        paper_info_html_path = os.path.join("working", "html", str(year), str(paper_id)+".html")
        if not os.path.exists(paper_info_html_path):
            r = requests.get(info_link)
            if not os.path.exists(os.path.dirname(paper_info_html_path)):
                os.makedirs(os.path.dirname(paper_info_html_path))
            with open(paper_info_html_path, "wb") as f:
                f.write(r.content)
        with open(paper_info_html_path, "rb") as f:
            html_content = f.read()
        paper_soup = BeautifulSoup(html_content, "lxml")
        try: 
            abstract = paper_soup.find('p', attrs={"class": "abstract"}).contents[0]
        except:
            print("Abstract not found %s" % paper_title.encode("ascii", "replace"))
            print ("For reference: ",year, " ", paper_id)
            abstract = ""
        authors = [(re.findall(r"-(\d+)$", author.contents[0]["href"])[0],
                    author.contents[0].contents[0])
                   for author in paper_soup.find_all('li', attrs={"class": "author"})]
        for author in authors:
            nips_authors.add(author)
            paper_authors.append([len(paper_authors)+1, paper_id, author[0]])
        event_types = [h.contents[0][23:] for h in paper_soup.find_all('h3') if h.contents[0][:22]=="Conference Event Type:"]
        if len(event_types) != 1:
            #print(event_types)
            #print([h.contents for h in paper_soup.find_all('h3')].__str__().encode("ascii", "replace"))
            #raise Exception("Bad Event Data")
            event_type = ""
        else:
            event_type = event_types[0]
        with open(pdf_path, "rb") as f:
            if f.read(15)==b"<!DOCTYPE html>":
                print("PDF MISSING")
                continue
        paper_text = text_from_pdf(pdf_path, temp_path)
        papers.append([paper_id, year, paper_title, event_type, pdf_name, abstract, paper_text])
        
    strUntilYear_csv = "2008_to_"+year+".csv"
    strUntilYear_pickle = "2008_to_"+year+".pickle"
    pd.DataFrame(list(nips_authors), columns=["id","name"]).sort_values(by="id").to_csv("output/authors"+strUntilYear_csv, index=False)
    pd.DataFrame(papers, columns=["id", "year", "title", "event_type", "pdf_name", "abstract", "paper_text"]).sort_values(by="id").to_csv("output/papers"+strUntilYear_csv, index=False)
    pd.DataFrame(paper_authors, columns=["id", "paper_id", "author_id"]).sort_values(by="id").to_csv("output/paper_authors"+strUntilYear_csv, index=False)
    pd.DataFrame(list(nips_authors), columns=["id","name"]).sort_values(by="id").to_pickle("output/authors"+strUntilYear_pickle)
    pd.DataFrame(papers, columns=["id", "year", "title", "event_type", "pdf_name", "abstract", "paper_text"]).sort_values(by="id").to_pickle("output/papers"+strUntilYear_pickle)
    pd.DataFrame(paper_authors, columns=["id", "paper_id", "author_id"]).sort_values(by="id").to_pickle("output/paper_authors"+strUntilYear_pickle)

pd.DataFrame(list(nips_authors), columns=["id","name"]).sort_values(by="id").to_csv("output/authors.csv", index=False)
pd.DataFrame(papers, columns=["id", "year", "title", "event_type", "pdf_name", "abstract", "paper_text"]).sort_values(by="id").to_csv("output/papers.csv", index=False)
pd.DataFrame(paper_authors, columns=["id", "paper_id", "author_id"]).sort_values(by="id").to_csv("output/paper_authors.csv", index=False)

# also pickling for easy access
print ("Remember, these pickles will work only for the following Python version:",sys.version)
pd.DataFrame(list(nips_authors), columns=["id","name"]).sort_values(by="id").to_pickle("output/authors.pickle")
pd.DataFrame(papers, columns=["id", "year", "title", "event_type", "pdf_name", "abstract", "paper_text"]).sort_values(by="id").to_pickle("output/papers.pickle")
pd.DataFrame(paper_authors, columns=["id", "paper_id", "author_id"]).sort_values(by="id").to_pickle("output/paper_authors.pickle")

print("Total Time Elapsed: {} mins".format(str(int((datetime.now()-startime).seconds/60))))