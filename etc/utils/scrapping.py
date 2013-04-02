'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

#quick and dirty scrapper to get number of downloads

import datetime
import mechanize
import BeautifulSoup as bs


def get_from_bitbucket():

    print("Get info from bitbucket\n")

    br = mechanize.Browser()
    br.open("https://bitbucket.org/gaubert/gmvault-official-download/downloads")

    response = br.response().read()

    #print("response = %s\n" % response)

    soup = bs.BeautifulSoup(response)

    #body_tag = soup.body
    all_tables = soup.findAll('table')

    table = soup.find(lambda tag: tag.name=='table' and tag.has_key('id') and tag['id']=="uploaded-files")

    rows = table.findAll(lambda tag: tag.name=='tr')

    res = {} 
    for row in rows:
       
       tds = row.findAll(lambda tag: tag.name == 'td')

       #print("tds = %s\n" %(tds))   

       td_number = 0
       name = None
       for td in tds:
           if td_number == 0:
              #print("td.a.string = %s\n" %(td.a.string))
              name = td.a.string
              res[name] = 0
           elif td_number == 3:
              #print("download nb = %s\n" %(td.string))
              res[name] = int(td.string)
           elif td_number == 4:
              #reset it
              td_number = 0
              name = None

           td_number += 1
           #print("td = %s\n" %(td))

    return res

def get_from_pypi(url):
 
    res = {}

    print("Get info from pypi (url= %s)\n" % (url))

    br = mechanize.Browser()
    br.open(url)

    response = br.response().read()

    soup = bs.BeautifulSoup(response)

    table = soup.find(lambda tag: tag.name == 'table')
    #print("all_tables = %s\n" % (all_tables))

    rows = table.findAll(lambda tag: tag.name == 'tr')

    #print("rows = %s\n" %(rows))

    for row in rows:
       
       tds = row.findAll(lambda tag: tag.name == 'td')

       #print("tds = %s\n" %(tds))   

       #ignore tds that are too small 
       if len(tds) < 6:
          #print("ignore td = %s\n" % (tds))
          continue

       td_number = 0
       name = None
       for td in tds:
           #print("td = %s\n" % (td))
           if td_number == 0:
              #print("td.a = %s\n" %(td.a))
              name = 'pypi-%s' % (td.a.string)
              res[name] = 0
           elif td_number == 5:
              #print("download nb = %s\n" %(td.string))
              res[name] = int(td.string)
           elif td_number == 6:
              #reset it
              td_number = 0
              name = None

           td_number += 1

    return res

if __name__ == "__main__":

    res = get_from_bitbucket()
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.8-beta"))
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.7-beta"))

    print("name , nb_downloads") 
    total = 0
    win_total = 0
    lin_total = 0
    mac_total = 0
    v17_total = 0
    v18_total = 0 
    for key in res.keys():
        if key.endswith(".exe"):
           win_total += res[key] 
        elif "macosx" in key:
           mac_total += res[key]
        else:
           lin_total += res[key]

        if "v1.8" in key:
           v18_total += res[key]
        elif "v1.7" in key:
           v17_total += res[key]

        #print("%s, %s\n" % (key, res[key]))
        total += res[key]

    print("as of today %s, total of downloads (v1.7 and v1.8) = %s." %(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),total))
    print("win total = %s,\nmac total = %s,\nlin total = %s." % (win_total, mac_total, lin_total))
    print("v1.7x total = %s since (17-12-2012), v1.8x = %s since (19-03-2013)" % (v17_total, v18_total))

