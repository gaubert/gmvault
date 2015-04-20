'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <since 2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

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

import json
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

V17W1_BETA_ON_GITHUB=7612
V17_BETA_SRC_ON_GITHUB=1264
V17_BETA_MAC_ON_GITHUB=2042

WIN_TOTAL_PREVIOUS_VERSIONS=2551+4303+3648+302+V17W1_BETA_ON_GITHUB
MAC_TOTAL_PREVIOUS_VERSIONS=2151+1806+1119+V17_BETA_MAC_ON_GITHUB
PYPI_TOTAL_PREVIOUS_VERSIONS=872+1065+826
SRC_TOTAL_PREVIOUS_VERSIONS=970+611+V17_BETA_SRC_ON_GITHUB
#LINUX is all Linux flavours available
LIN_TOTAL_PREVIOUS_VERSIONS=916+325+254+SRC_TOTAL_PREVIOUS_VERSIONS+PYPI_TOTAL_PREVIOUS_VERSIONS
TOTAL_PREVIOUS_VERSIONS=2551+2155+916+872+4303+1806+325+970+1065+3648+1119+254+611+826+302+V17_BETA_MAC_ON_GITHUB+V17_BETA_SRC_ON_GITHUB+V17W1_BETA_ON_GITHUB

def get_stats(return_type):
    """ return the stats """
    res = get_from_bitbucket()
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.8.1-beta"))
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.8-beta"))
    res.update(get_from_pypi("https://pypi.python.org/pypi/gmvault/1.7-beta"))

    #print("name , nb_downloads") 
    total = 0
    win_total   = 0
    lin_total   = 0
    mac_total   = 0
    v17_total   = 0
    v18_total   = 0 
    v181_total  = 0 
    pypi_total  = 0
    src_total   = 0
    for key in res.keys():
        #print("key= %s: (%s)\n" %(key, res[key]))
        if key.endswith(".exe"):
           win_total += res[key] 
        elif "macosx" in key:
           mac_total += res[key]
        else:
           lin_total += res[key]

        if "1.8" in key:
           #print("inv1.8: %s" % (key))
           v18_total += res[key]
        elif "1.7" in key:
           v17_total += res[key]

        if "src" in key:
           src_total += res[key]
        elif "pypi" in key:
           pypi_total += res[key]

        if "1.8.1" in key:
          v181_total += res[key]

        #print("%s, %s\n" % (key, res[key]))
        total += res[key]

    total      += TOTAL_PREVIOUS_VERSIONS 
    win_total  += WIN_TOTAL_PREVIOUS_VERSIONS
    lin_total  += LIN_TOTAL_PREVIOUS_VERSIONS
    mac_total  += MAC_TOTAL_PREVIOUS_VERSIONS
    pypi_total += PYPI_TOTAL_PREVIOUS_VERSIONS  
    src_total  += SRC_TOTAL_PREVIOUS_VERSIONS

    the_str = ""
    if return_type == "TEXT":

        the_str += "As of today %s, total of downloads (v1.7 and v1.8) = %s.\n" %(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),total)
        the_str += "win total = %s,\nmac total = %s,\nlin total = %s.\n" % (win_total, mac_total, lin_total)
        the_str += "pypi total = %s, src total = %s since .\n" % (pypi_total, src_total)
        the_str += "v1.7x total = %s since (17-12-2012), v1.8x = %s since (19-03-2013).\n" % (v17_total, v18_total)
        the_str += "v1.8.1 total = %s since (28.04.2013).\n" % (v181_total)

        return the_str

    elif return_type == "JSON":
        return json.dumps({'total' : total, 'now' : datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), \
                    'win_total' : win_total, 'mac_total' : mac_total, 'lin_total' : lin_total, \
                    "pypi_total" : pypi_total, "src_total" : src_total, \
                    'v17x_total' : v17_total, 'v18x_total' : v18_total, 'v181_total': v181_total})

if __name__ == "__main__":

    print(get_stats("JSON"))


