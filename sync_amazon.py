#!/usr/bin/python
#
# sync_amazon.py
#
# uses a MySQL database to connect to ebay's search API, and return results to the database
#
# 2014.05.10 eXpressTek Inc, initial release (Warren Kenner)
#

import bottlenose
import xmltodict
import xml.etree.ElementTree as ElementTree
import json
import MySQLdb
import credentials
import time
import sys
import re

debug = True

#do a version check
version_check = subprocess.check_output(['git', 'diff', 'origin/master'])
if (version_check.strip() != ""):
    print "WARN: This software may be out of date. Please see about updating"

#make a timestamp
def stamp():
  return time.strftime("%a, %d %b %Y %H:%M:%S +0000",time.gmtime())

#get the credentials for the database from the db.conf file. (the import credentials is the actual function to do this.)
creds = credentials.load_file_config()

#connect to the database
db = MySQLdb.connect(host=creds['host'], port=int(creds['port']), user=creds['user'], passwd=creds['password'], db=creds['database'])

#initate a cursor
cursor = db.cursor()

######################################
# grab the Amazon credentials from the config table of the database
######################################
cursor.execute("SELECT * FROM sync_config WHERE Sync_Type LIKE 'Amazon'")

#get the return values
dbreturn = cursor.fetchall()

#unpack from the array and then unpack from tuple
key_tuple = dbreturn[0]
synctype, syncvalue, synckey = key_tuple

#reconstitute the json to a dictionary 
keydict = json.loads(synckey)

######################################
# grab the searches from the database
######################################

#connect to amazon
amazon = bottlenose.Amazon(str(keydict['keyID'].decode('ascii', 'ignore')), str(keydict['secret'].decode('ascii', 'ignore')), str(keydict['associate_id'].decode('ascii', 'ignore')))

#get the searches
cursor.execute("SELECT * FROM sync_searches WHERE search_poller LIKE 'amazon'")

#get the return values
search_return = cursor.fetchall()

#if nothing returned, exit
if search_return is 0L:
    print "{0} No searches to run, exiting".format(stamp())
    sys.exit(0)

#run for each search returned
for search_tuple in search_return:

    # unpack search tuple to get search text
    search_num, search_poller, search_text = search_tuple
    
    # encode search text as string
    if debug:
        print "search is: "+search_text
    search_text = search_text.encode('ascii','ignore')

    #run the item search, get the response as XML and convert to dictionary
    response = amazon.ItemSearch(Keywords=search_text, SearchIndex="All")
    xmldict = xmltodict.parse(response)
    
    #index to the Item level
    items = xmldict['ItemSearchResponse']['Items']['Item']
    
    #for each item in the Items map the responses to the relevant database fields
    for item in items:
        # gets the information about the items
        itemLookupInfo = amazon.ItemLookup(ItemId=item['ASIN'], ResponseGroup="Large")
        itemXMLdict = xmltodict.parse(itemLookupInfo)
        itemInfo = itemXMLdict['ItemLookupResponse']['Items']['Item']
        if debug:
            print json.dumps(itemXMLdict)
        
        #mappings for the database fields
        sku = itemInfo['ASIN']
        poller_type = "amazon"
        images = itemInfo['MediumImage']['URL']
        lastUpdate = time.time()
        category = itemInfo['ItemAttributes']['ProductGroup']
        dirty_subcategory = itemInfo['BrowseNodes']['BrowseNode']
        subcategory = []
        for sub in dirty_subcategory:
            subcategory.append(sub['Name']+" ")
        price = float(itemInfo['ItemAttributes']['ListPrice']['Amount'])/100
        currency = itemInfo['ItemAttributes']['ListPrice']['CurrencyCode']
        dirty_description = itemInfo['ItemAttributes']['Feature']
        description = []
        #sanitize the description
        for desc in dirty_description:
            if debug:
                print desc
            desc = re.sub('\\\\', '', desc)
            description.append(desc)
        title = itemInfo['ItemAttributes']['Title']
        seller = itemInfo['ItemAttributes']['Publisher']
        url = itemInfo['DetailPageURL']
        
        if debug:
            print ""
            print ""
            print "INFO:"
            print ""
            print sku 
            print poller_type
            print images 
            print lastUpdate 
            print category
            print subcategory
            print price 
            print currency
            print description
            print title
            print seller
            print url
            print ""
            print ""
            sys.exit(0)
        
        #print progress of SKU's with timestamp
        print "{1} got_sku={0}".format(sku,stamp()),
        
        # check if its already in the database
        recordNum = cursor.execute("SELECT * FROM sync WHERE ItemID LIKE '{0}'".format(sku))

        # initialize the sql_statement
        sql_statement = ''

        # if its not in the database, INSERT the new record
        if (recordNum == 0L) or (recordNum == 0):
        
            print "sku does NOT exist INSERT'ing new entry"
            sql_statement = u"""INSERT INTO sync (ItemID, Type, Images, LastUpdate, Category, Price, CurrencyID, Description, Title, Seller, URL, subcategory) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', {5}, '{6}', '{7}', '{8}', '{9}', '{10}','{11}')""".format(
             sku,
             db.escape_string(poller_type),
             db.escape_string(json.dumps(images)),
             lastUpdate,
             db.escape_string(category),
             price,
             db.escape_string(currency),
             db.escape_string(json.dumps(description)),
             db.escape_string(title),
             db.escape_string(seller),
             db.escape_string(url),
             db.escape_string(json.dumps(subcategory))
            )

        # else its an existing record and we need to update
        else:
            print "sku does exist UPDATE'ing the EXISTING entry"
            sql_statement = u"""UPDATE sync SET Type='{0}', Images='{1}', LastUpdate='{2}', Category='{3}', Price={4}, CurrencyID='{5}', Description='{6}', Title='{7}', Seller='{8}', URL='{9}', subcategory='{10}' WHERE ItemID='{11}'""".format(
             db.escape_string(poller_type),
             db.escape_string(json.dumps(images)),
             lastUpdate,
             db.escape_string(category),
             price,
             db.escape_string(currency),
             db.escape_string(json.dumps(description)),
             db.escape_string(title),
             db.escape_string(seller),
             db.escape_string(url),
             db.escape_string(json.dumps(subcategory)),
             sku
            )

#        print "{0} DEBUG: {1}".format(stamp(),sql_statement)
        cursor.execute(sql_statement)

        # make it sleep a tick before starting the next record to allow for rate-limiting behavior
        time.sleep(.3)

print "{0} sync_amazon.py complete".format(stamp())
