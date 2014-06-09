#!/usr/bin/python
#
# sync_ebay.py
#
# uses a MySQL database to connect to ebay's search API, and return results to the database
#
# 2014.05.10 eXpressTek Inc, initial release (Warren Kenner)
#

from ebaysdk.finding import Connection as finding
from ebaysdk.shopping import Connection as shopping
import json
import time
import credentials
import MySQLdb
import sys
import inspect
import subprocess

#make a timestamp
def stamp():
  return time.strftime("%a, %d %b %Y %H:%M:%S +0000 ",time.gmtime())

debug = False
timing = False
smallDescription = False

#this is to get the connections to be quiet.
class ConnectionError(Exception):
    pass

if timing:
    print stamp()+"doing a version check"
#do a version check
#version_check = subprocess.check_output(['git', 'diff', 'origin/master'])
#if (version_check.strip() != ""):
#    print "WARN: This software may be out of date. Please see about updating"

if timing:
    print stamp()+"getting creds from files and database"
#get the credentials for the database from the db.conf file. (the import credentials is the actual function to do this.)
creds = credentials.load_file_config()

if timing:
    print stamp()+"connecting to the database"
#connect to the database
db = MySQLdb.connect(host=creds['host'], port=int(creds['port']), user=creds['user'], passwd=creds['password'], db=creds['database'])

#initate a cursor
cursor = db.cursor()

######################################
# grab the ebay credentials from the config table of the database
######################################
cursor.execute("SELECT * FROM sync_config WHERE Sync_Type LIKE 'ebay'")

#get the return values
dbreturn = cursor.fetchall()

#unpack from the array and then unpack from tuple
key_tuple = dbreturn[0]
synctype, syncvalue, synckey = key_tuple

#reconstitute the json to a dictionary 
keydict = json.loads(synckey)
if timing:
    print stamp()+"got creds - Finding Searches"
######################################
# grab the searches from the database
######################################
cursor.execute("SELECT * FROM sync_searches WHERE search_poller LIKE 'ebay'")

#get the return values
search_return = cursor.fetchall()
if search_return is 0L:
    print "{0} No searches to run, exiting".format(stamp())
    sys.exit(0)

#run for each search returned
for search_tuple in search_return:
    if timing:
        print stamp()+"running searches"
    
    # unpack search tuple to get search text
    search_num, search_poller, search_text, number_of_results = search_tuple
    
    print stamp()+"running search \""+search_text+"\""
    
    results = 0
    while (results <= number_of_results):
        # encode search text as string
        search_text = search_text.encode('ascii','ignore')
        try:
            # establish connection using key obtained from database
            find = finding(appid=keydict['key'])
            if timing:
                print stamp()+"about to make api call"
            #execute the search once connected. er
            
            num_to_search = 100
            if number_of_results < 100:
                num_to_search = number_of_results
            page = int(results/num_to_search)
            find.execute('findItemsAdvanced', {'keywords': search_text, 'paginationInput':{'entriesPerPage':num_to_search, 'pageNumber':(page+1)}, 'itemFilter':{'name':'ListingType','value':'AuctionWithBIN'}, 'itemFilter':{'name':'ListingType','value':'FixedPrice'}})
            if timing:
                print stamp()+"finished making api call (executed)"
        except ConnectionError as e:
            print "got a Connection Error"
            raise e
            sys.exit(0)
        #get the response dictionary from the call
        mydict = find.response_dict()
        if debug:
            print "mydict: "
            print mydict
        #unpack the return items and map to relevant Database fields
        if timing:
            print stamp()+"getting each item"
        items = mydict['searchResult']['item']
        
        for item in items:
            sku = item['itemId']['value']
            poller_type = "ebay"
            seller = ''
            images = ''
            if "galleryURL" in item.keys():
                if "value" in item['galleryURL'].keys():
                    images = item['galleryURL']['value']
            lastUpdate = time.time()
            category = item['primaryCategory']['categoryName']['value']
            price = item['sellingStatus']['currentPrice']['value']
            currency = item['sellingStatus']['currentPrice']['currencyId']['value']
            title = item['title']['value']
            url = item['viewItemURL']['value']
            #print progress of SKU's with timestamp
            print "{1} got_sku={0}".format(sku,stamp()),
            
            # check if its already in the database
            recordNum = cursor.execute("SELECT * FROM sync_ebay WHERE ItemID LIKE '{0}'".format(sku))
    
            # initialize the sql_statement
            sql_statement = ''
            
            # if its not in the database, INSERT the new record
            try:
                if (recordNum == 0L) or (recordNum == 0):
                
                    print "sku does NOT exist INSERT'ing new entry"
                    sql_statement = u"""INSERT INTO sync_ebay (ItemID, Type, Images, LastUpdate, Category, Price, CurrencyID, Title, Seller, URL) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', {5}, '{6}', '{7}', '{8}', '{9}')""".format(
                     sku,
                     db.escape_string(poller_type),
                     db.escape_string(images),
                     lastUpdate,
                     db.escape_string(category),
                     price,
                     db.escape_string(currency),
                     db.escape_string(title),
                     db.escape_string(seller),
                     db.escape_string(url)
                    )
                    
                
                # else its an existing record and we need to update
                else:
                    print "sku does exist UPDATE'ing the EXISTING entry"
                    sql_statement = u"""UPDATE sync_ebay SET Type='{0}', Images='{1}', LastUpdate='{2}', Category='{3}', Price={4}, CurrencyID='{5}', Title='{6}', Seller='{7}', URL='{8}' WHERE ItemID={9}""".format(
                     db.escape_string(poller_type),
                     db.escape_string(images),
                     lastUpdate,
                     db.escape_string(category),
                     price,
                     db.escape_string(currency),
                     db.escape_string(title),
                     db.escape_string(seller),
                     db.escape_string(url),
                     db.escape_string(sku)
                    )
                
    #            print "{0} DEBUG: {1}".format(stamp(),sql_statement)
                cursor.execute(sql_statement)
            except UnicodeEncodeError as err:
                if debug:
                    print err
                print stamp()+"Malformed Data - Unicode Encode Error - Skipping"
                results = results + 1
                continue
            results = results + 1
    
            
print "{0} sync_ebay.py complete".format(stamp())
