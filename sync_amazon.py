#!/usr/bin/python
#
# sync_amazon.py
#
# uses a MySQL database to connect to ebay's search API, and return results to the database
#
# 2014.05.10 eXpressTek Inc, initial release (Warren Kenner)
#

from amazonproduct import API
from lxml import etree
#import bottlenose
import xmltodict
import xml.etree.ElementTree as ElementTree
import json
import MySQLdb
import credentials
import time
import sys
import re
import subprocess

debug = False

#make a timestamp
def stamp():
  return time.strftime("%a, %d %b %Y %H:%M:%S +0000",time.gmtime())

#do a version check
#version_check = subprocess.check_output(['git', 'diff', 'origin/master'])
#if (version_check.strip() != ""):
#    print "WARN: This software may be out of date. Please see about updating"

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

if debug:
    print type(synckey)
    print synckey

#reconstitute the json to a dictionary (one made out of strings)
unikeydict = json.loads(synckey)
if debug:
    print unikeydict
    print dir(unikeydict)
keydict = {}
keys = unikeydict.keys()
if debug:
    print keys
for key in keys:
    keydict[key]=str(unikeydict[key].decode('ascii', 'ignore'))

if debug:
    print keydict
#give the api the connection information
api = API(locale='us',cfg=keydict)

######################################
# grab the searches from the database
######################################

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
    search_num, search_poller, search_text, number_of_results = search_tuple
    
    # encode search text as string
    if debug:
        print "search is: "+search_text
    search_text = search_text.encode('ascii','ignore')

    #run the item search, get the response as XML and convert to dictionary
    response =  api.item_search("All", Keywords=search_text)
    if debug:
        print response
        print response.results
        print response.pages
    #xmldict = xmltodict.parse(response)
    
    #index to the Item level
    #items = xmldict['ItemSearchResponse']['Items']['Item']
    
    #for each item in the Items map the responses to the relevant database fields
    results = 0
    while results <= number_of_results:
        for item in response:
            if results > number_of_results:
                break
            if debug:
                print dir(item)
            # gets the information about the items
            ASIN = str(item['ASIN'])
            itemLookupInfo = api.item_lookup(ASIN, ResponseGroup="Large")
            if debug:
                print dir(itemLookupInfo)
            xmlInfo = etree.tostring(itemLookupInfo)
            itemXMLdict = xmltodict.parse(xmlInfo)
            if debug:
                print dir(itemXMLdict)
                print itemXMLdict.keys()
            itemInfo = itemXMLdict['ItemLookupResponse']['Items']['Item']
            
            #mappings for the database fields
            try:
                sku = itemInfo['ASIN']
                poller_type = "amazon"
                images = ""
                if 'MediumImage' in itemInfo.keys():
                    images = itemInfo['MediumImage']['URL']
                lastUpdate = time.time()
                category = itemInfo['ItemAttributes']['ProductGroup']
                dirty_subcategory = itemInfo['BrowseNodes']['BrowseNode']
                subcategory = ""
                for sub in dirty_subcategory:
                    try:
                        subcategory = subcategory + sub['Name'] + " "
                    except TypeError as e:
                        try:
                            for sub_sub in sub:
                                subcategory = subcategory + sub_sub['Name']+" "
                        except TypeError as f:
                            subcategory = "None"
                subcategory = str(subcategory)
                price = {}
                if 'ListPrice' in itemInfo['ItemAttributes'].keys():
                    price['ListPrice'] = {}
                    if 'Amount' in itemInfo['ItemAttributes']['ListPrice'].keys():
                        price['ListPrice']['Amount'] = float(itemInfo['ItemAttributes']['ListPrice']['Amount'])/100
                        price['ListPrice']['Currency'] = itemInfo['ItemAttributes']['ListPrice']['CurrencyCode']
                    else:
                        price['LowestNewPrice']['Currency'] = "Price Exists, No Amount Listed"
                if 'OfferSummary' in itemInfo.keys():
                    if 'LowestUsedPrice' in itemInfo['OfferSummary'].keys():
                        price['LowestUsedPrice'] = {}
                        if 'Amount' in itemInfo['OfferSummary']['LowestUsedPrice'].keys():
                            price['LowestUsedPrice']['Amount'] = float(itemInfo['OfferSummary']['LowestUsedPrice']['Amount'])/100
                            price['LowestUsedPrice']['Currency'] = itemInfo['OfferSummary']['LowestUsedPrice']['CurrencyCode']
                        else:
                            price['LowestNewPrice']['Currency'] = "Price Exists, No Amount Listed"
                    if 'LowestNewPrice' in itemInfo['OfferSummary'].keys():
                        price['LowestNewPrice'] = {}
                        if 'Amount' in itemInfo['OfferSummary']['LowestNewPrice'].keys():
                            price['LowestNewPrice']['Amount'] = float(itemInfo['OfferSummary']['LowestNewPrice']['Amount'])/100
                            price['LowestNewPrice']['Currency'] = itemInfo['OfferSummary']['LowestNewPrice']['CurrencyCode']
                        else:
                            price['LowestNewPrice']['Currency'] = "Price Exists, No Amount Listed"
                single_price = ""
                single_price_currency = ""
                if 'ListPrice' in price.keys():
                    single_price = price['ListPrice']['Amount']
                    single_price_currency = price['ListPrice']['Currency']
                else:
                    if price != {}:
                        single_price = price[price.keys()[0]]['Amount']
                        single_price_currency = price[price.keys()[0]]['Currency']
                description = ""
                if 'Feature' in itemInfo['ItemAttributes'].keys():
                    dirty_description = itemInfo['ItemAttributes']['Feature']
                    #sanitize the description
                    for desc in dirty_description:
                        if debug:
                            print str(desc).decode('ascii', 'ignore')
                        desc = re.sub('\\\\', '', desc)
                        description = description + desc
                else:
                    description = "None"
                title = itemInfo['ItemAttributes']['Title']
                seller = ""
                if 'Publisher' in itemInfo['ItemAttributes'].keys():
                    seller = itemInfo['ItemAttributes']['Publisher']
                url = itemInfo['DetailPageURL']
                manufacturer = ""
                if 'Manufacturer' in itemInfo['ItemAttributes'].keys():
                    manufacturer = itemInfo['ItemAttributes']['Manufacturer']
                brand = ""
                if 'Brand' in itemInfo['ItemAttributes'].keys():
                    brand = itemInfo['ItemAttributes']['Brand']
            except KeyError as err:
                if debug:
                    print err.message
                    print json.dumps(itemInfo)
                print stamp()+" got malformed data from amazon at or around "+err.message+", skipping."
                continue
            
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
                
            
            #print progress of SKU's with timestamp
            print "{1} got_sku={0}".format(sku,stamp()),
            try:
                # check if its already in the database
                recordNum = cursor.execute("SELECT * FROM sync_amazon WHERE ItemID LIKE '{0}'".format(sku))
                
                # initialize the sql_statement
                sql_statement = ''
                
                # if its not in the database, INSERT the new record
                if (recordNum == 0L) or (recordNum == 0):
                
                    print "sku does NOT exist INSERT'ing new entry"
                    sql_statement = u"""INSERT INTO sync_amazon (ItemID, Type, Images, Category, Price, Currency, AllPrices, Description, Title, Seller, subcategory, URL, Brand, Manufacturer, LastUpdate) VALUES ('{0}', '{1}', '{2}', '{3}', {4}, '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', {14})""".format(
                     db.escape_string(sku.encode('utf-8')),
                     db.escape_string(poller_type.encode('utf-8')),
                     db.escape_string(images.encode('utf-8')),
                     db.escape_string(category.encode('utf-8')),
                     float(single_price),
                     db.escape_string(single_price_currency.encode('utf-8')),
                     db.escape_string(json.dumps(price).encode('utf-8')),
                     db.escape_string(json.dumps(description).encode('utf-8')),
                     db.escape_string(title.encode('utf-8')),
                     db.escape_string(seller).encode('utf-8'),
                     db.escape_string(subcategory.encode('utf-8')),
                     db.escape_string(url.encode('utf-8')),
                     db.escape_string(brand.encode('utf-8')),
                     db.escape_string(manufacturer.encode('utf-8')),
                     float(lastUpdate)
                    )
                
                # else its an existing record and we need to update
                else:
                    print "sku does exist UPDATE'ing the EXISTING entry"
                    sql_statement = u"""UPDATE sync_amazon SET Type='{0}', Images='{1}', LastUpdate='{2}', Category='{3}', Price={4}, Currency='{5}', AllPrices='{6}', Description='{7}', Title='{8}', Seller='{9}', URL='{10}', subcategory='{11}' WHERE ItemID='{12}'""".format(
                     db.escape_string(poller_type),
                     db.escape_string(images),
                     float(lastUpdate),
                     db.escape_string(category),
                     float(single_price),
                     db.escape_string(single_price_currency),
                     db.escape_string(json.dumps(price).encode('utf-8')),
                     db.escape_string(str(json.dumps(description).decode('ascii', 'ignore'))),
                     db.escape_string(str(title.decode('ascii', 'ignore'))),
                     db.escape_string(seller),
                     db.escape_string(url),
                     db.escape_string(json.dumps(subcategory)),
                     db.escape_string(sku)
                    )
                
#                print "{0} DEBUG: {1}".format(stamp(),sql_statement)
                cursor.execute(sql_statement)
                
                # make it sleep a tick before starting the next record to allow for rate-limiting behavior
                time.sleep(.3)
            except UnicodeDecodeError as u:
                if debug:
                    print u
                print stamp()+" Malformed Data - Unicode Decode Error - Skipping"
                results = results + 1
                continue
            results = results + 1

print "{0} sync_amazon.py complete".format(stamp())
    