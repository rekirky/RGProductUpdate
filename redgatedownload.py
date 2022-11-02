import requests
import xmltodict
import urllib.request
import re
from datetime import datetime, date
import csv
from csv import DictReader
from bs4 import BeautifulSoup

#to-do 
#add functionality to check for changes since last update / last week

def main():
    #testing - use a shorter list / change test to True
    test = True
    if test == True:
        common = ['SQLBackup','SQLDataCompare','FlywayDesktop']
        prod_list = get_updates(common)
    else:
        products = get_products()
        prod_list = get_updates(products)
    create_html(prod_list)
    create_css()
    create_js()

def get_products():
    product = []
    url = f"https://redgate-download.s3.eu-west-1.amazonaws.com/?delimiter=/&prefix=checkforupdates/"
    file = urllib.request.urlopen(url)
    data = file.read()
    file.close()
    data = xmltodict.parse(data)
    for i in data["ListBucketResult"]["CommonPrefixes"]:
        product.append(i["Prefix"].replace("checkforupdates/","").replace("/",""))
    return(product)
        
def get_updates(products):
    prod_list = []
    for i in products:
        link = ""
        date = ""
        url = f"https://redgate-download.s3.eu-west-1.amazonaws.com/?delimiter=/&prefix=checkforupdates/{i}/"
        file = urllib.request.urlopen(url)
        data = file.read()
        file.close()
        data = xmltodict.parse(data)
        try:
            for x in data:
                date = data["ListBucketResult"]["Contents"]["LastModified"]
                key = data["ListBucketResult"]["Contents"]["Key"]
                link = f"https://download.red-gate.com/{key}"
        except:
            try:
                for y in data["ListBucketResult"]["Contents"]:
                    if (y["LastModified"]) > date:
                        date = y["LastModified"]
                        link = f"https://download.red-gate.com/{y['Key']}"
            except:
                pass
        prod_list.append([{"product":i,"link":link,"date":date}])
    return(prod_list)
    
def create_html(prod_list):
    
    file_out = open(f"index.html","w")
    file_out.write("<head>\n<title>Redgate Product Download Links</title>\n")
    file_out.write("<link rel='stylesheet' href='https://cdn.rd.gt/assets/styles/isw.css?v=1637587319771'>\n<link rel='stylesheet' href='redgate.css'>\n")
    file_out.write("<link rel='icon type='image/x-icon' href='favicon.ico'>\n</head>\n")
    file_out.write("<body>\n<script src='redgate.js'></script>\n")
    file_out.write(f"<h1>Redgate Product Links</h1>\n\t")
    file_out.write(f"<div>Links to the most recent version of Redgate products allowing searching by product & release date</div>\n\t")
    file_out.write(f"<div>Products updated this year are Green, last year Orange & previous years Red</div>\n\t")
    file_out.write(f"<div>Tooltips may be available when hovering over products updated this year</div>\n\t")
    file_out.write(f"This is a passion project and is an ongoing work in progress</div>\n")
    file_out.write(f"<h2>Page updated: {date.today().strftime('%Y/%m/%d')} | {datetime.now().strftime('%H:%M:%S')}</h2>\n\n")
    file_out.write(f"<input type='text' id='myInput' onkeyup='myFunction()' placeholder='Search by product..'>\n")
    file_out.write(f"<input type='text' id='myYear' onkeyup='myFilter()' placeholder='Search by updated date..'>\n")
    file_out.write("<ul id = 'myUL'>\n\t")
    for i in prod_list:
        for x in i:
            xproduct = x['product']
            xlink = x['link']
            xdate = x['date'][0:10]
            try:
                if int(xdate[0:4]) == date.today().year:
                    xclass = 'current'
                elif int(xdate[0:4]) == date.today().year -1:
                    xclass = 'previous'
                else:
                    xclass = 'old'
            except:
                xclass = 'old'
            try:
                tooltip=""
                ver = re.search("[0-9]*\.[0-9]*\.[0-9]*",xlink)
                tooltip = patch_notes(xproduct)
                file_out.write(f"<li title='{tooltip}' class={xclass}>\n\t\t<a href={xlink}><b>{xproduct} - {ver.group()}</b></a><span> - Updated {xdate}</span></li>\n\t")
            except:
                file_out.write(f"<li class={xclass}>\n\t\t<a href={xlink}><b>{xproduct}</b></a><span> - Updated {xdate}</span></li>\n\t")
    file_out.write(f"</ul>\n</body>\n")
    file_out.close()    

def create_css(): #write the css file
    file_out = open(f"redgate.css","w")
    file_out.write("body {\n\tbackground:whitesmoke;\n}\n")
    file_out.write("h1 {\n\ttext-decoration: underline;\n}\n")
    file_out.write("ul .current {\n\tcolor:green;\n}\n")
    file_out.write("ul .previous {\n\tcolor:orange;\n}\n")
    file_out.write("ul .old {\n\tcolor:red;\n}\n")
    file_out.write("#myInput {\n\twidth: 25%;\n}\n")
    file_out.write("#myYear {\n\twidth: 25%;\n}\n")
    file_out.close()

def create_js(): #write the js file for searching
    file_out = open(f"redgate.js","w")
    file_out.write("function myFunction() {\n\tvar input, filter, ul, li, a, i, txtValue;\n\tinput = document.getElementById('myInput');\n\t")
    file_out.write("filter = input.value.toUpperCase();\n\tul = document.getElementById('myUL');\n\tli = ul.getElementsByTagName('li');\n\t")
    file_out.write("for (i = 0; i < li.length; i++) {\n\t\ta = li[i].getElementsByTagName('a')[0];\n\t\ttxtValue = a.textContent || a.innerText;\n\t\t")
    file_out.write("if (txtValue.toUpperCase().indexOf(filter) > -1) {\n\t\t\tli[i].style.display = '';\n\t\t} else {\n\t\t\t")
    file_out.write("li[i].style.display = 'none';\n\t\t}\n\t}\n}\n")
    
    file_out.write("function myFilter() {\n\tvar input, filter, ul, li, a, i, txtValue;\n\tinput = document.getElementById('myYear');\n\t")
    file_out.write("filter = input.value.toUpperCase();\n\tul = document.getElementById('myUL');\n\tli = ul.getElementsByTagName('li');\n\t")
    file_out.write("for (i = 0; i < li.length; i++) {\n\t\ta = li[i].getElementsByTagName('span')[0];\n\t\ttxtValue = a.textContent || a.innerText;\n\t\t")
    file_out.write("if (txtValue.toUpperCase().indexOf(filter) > -1) {\n\t\t\tli[i].style.display = '';\n\t\t} else {\n\t\t\t")
    file_out.write("li[i].style.display = 'none';\n\t\t}\n\t}\n}\n")
    file_out.close

def patch_notes(product_list):
    tool_tip = []
    with open('releasenotes.csv','r') as data:
        reader = csv.reader(data)
        url_dict = dict((rows[0], rows[1]) for rows in reader)
        data.close()
        link = f"{url_dict[product_list]}"
        url = requests.get(link)
        soup = BeautifulSoup(url.text,features="html.parser")
        for items in soup.find_all("h2",limit=1):
            for item in items.find_next_siblings():
                if item.name != 'h2':
                    for li in item:
                        tool_tip.append(li.get_text(strip=True))
                else:
                    break
    return(tool_tip_html(tool_tip))


def tool_tip_html(tool_tip):
    html = ""
    for i in tool_tip:
        html += i.replace('\n',' ')
        html += '&#013'
    return(html)



# run program
if __name__ == '__main__':
    main()


    
