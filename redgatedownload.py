import requests
import xmltodict
import urllib.request
import re
from datetime import datetime, date

#to-do 
#add functionality to check for changes since last update / last week

def main():
    print("Running Redgate Product Link program")
    #testing - use a shorter list / change test to True
    test = False
    if test == True:
        common = ['SQLBackup','SQLDataCompare','FlywayDesktop']
        prod_list = get_updates(common)
    else:
        products = get_products()
        prod_list = get_updates(products)
    create_html(prod_list)
    create_css()
    create_js()
    print("File created")

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
    file_out = open(f"c:\\temp\\Python Scratchpad\\file.html","w")
    file_out.write("<head>\n<title>Redgate Product Download Links</title>\n<link rel='stylesheet' href='https://cdn.rd.gt/assets/styles/isw.css?v=1637587319771'>\n<link rel='stylesheet' href='redgate.css'>\n</head>\n")
    file_out.write("<body>\n<script src='redgatetemp.js'></script>\n")
    file_out.write(f"<h1>Page updated: {date.today().strftime('%Y/%m/%d')} | {datetime.now().strftime('%H:%M:%S')}</h1>\n")
    file_out.write(f"<input type='text' id='myInput' onkeyup='myFunction()' placeholder='Search for product..'>")
    file_out.write(f"<input type='text' id='myYear' onkeyup='myFilter()' placeholder='Search for updated date..'>\n")
    file_out.write("<ul id = 'myUL'>\n")
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
                ver = re.search("[0-9]*\.[0-9]*\.[0-9]*",xlink)
                file_out.write(f"<li class={xclass}><a href={xlink}><b>{xproduct} - {ver.group()}</b></a><span> - Updated {xdate}</span></li>\n")
            except:
                file_out.write(f"<li class={xclass}><a href={xlink}><b>{xproduct}</b></a><span> - Updated {xdate}</span></li>\n")
    file_out.write(f"</ul>\n</body>\n")
    file_out.close()    

def create_css(): #write the css file
    file_out = open(f"c:\\temp\Python Scratchpad\\redgate.css","w")
    file_out.write("body {\n\tbackground:whitesmoke;\n}\n")
    file_out.write("h1 {\n\ttext-decoration: underline;\n}\n")
    file_out.write("ul .current {\n\tcolor:green;\n}\n")
    file_out.write("ul .previous {\n\tcolor:orange;\n}\n")
    file_out.write("ul .old {\n\tcolor:red;\n}\n")
    file_out.write("#myInput {\n\twidth: 25%;\n}")
    file_out.write("#myYear {\n\twidth: 25%;\n}")
    file_out.close()

def create_js(): #write the js file for searching
    file_out = open(f"c:\\temp\Python Scratchpad\\redgate.js","w")
    file_out.write("function myFunction() {\n\tvar input, filter, ul, li, a, i, txtValue;\n\tinput = document.getElementById('myInput');\n\t")
    file_out.write("filter = input.value.toUpperCase();\n\tul = document.getElementById('myUL');\n\tli = ul.getElementsByTagName('li');\n\t")
    file_out.write("for (i = 0; i < li.length; i++) {\n\t\ta = li[i].getElementsByTagName('a')[0];\n\t\ttxtValue = a.textContent || a.innerText;\n\t\t")
    file_out.write("if (txtValue.toUpperCase().indexOf(filter) > -1) {\n\t\t\tli[i].style.display = '';\n\t\t} else {\n\t\t\t")
    file_out.write("li[i].style.display = 'none';\n\t\t}\n\t}\n}")
    file_out.close

# run program
main()