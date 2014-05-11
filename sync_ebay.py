#!/usr/bin/python
#
# sync_ebay.py
#
# uses a MySQL database to connect to ebay's search API, and return results to the database
#
# 2014.05.10 eXpressTek Inc, initial release (Warren Kenner)
#

from ebaysdk.finding import Connection
import json
import time
import credentials
import MySQLdb

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
    
    # unpack search tuple to get search text
    search_num, search_poller, search_text = search_tuple
    
    # encode search text as string
    search_text = search_text.encode('ascii','ignore')
    
    try:
        # establish connection using key obtained from database
        api = Connection(appid=keydict['key'])
        #execute the search once connected. er
        api.execute('findItemsAdvanced', {'keywords': search_text})
    
    except ConnectionError as e:
        raise e
        sys.exit(0)
    
    #get the response dictionary from the call
    mydict = api.response_dict()
    
    #unpack the return items and map to relevant Database fields
    items = mydict['searchResult']['item']
    for item in items:
        sku = item['itemId']['value']
        poller_type = "ebay"
        seller = ''
        images = item['galleryURL']['value']
        lastUpdate = time.time()
        subcategory = ''
        category = item['primaryCategory']['categoryName']['value']
        price = item['sellingStatus']['currentPrice']['value']
        currency = item['sellingStatus']['currentPrice']['currencyId']['value']
        description = ''
        title = item['title']['value']
        url = item['viewItemURL']['value']
        raw = item
        
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
             db.escape_string(images),
             lastUpdate,
             db.escape_string(category),
             price,
             db.escape_string(currency),
             db.escape_string(description),
             db.escape_string(title),
             db.escape_string(seller),
             db.escape_string(url),
             db.escape_string(subcategory)
            )

        # else its an existing record and we need to update
        else:
            print "sku does exist UPDATE'ing the EXISTING entry"
            sql_statement = u"""UPDATE sync SET Type='{0}', Images='{1}', LastUpdate='{2}', Category='{3}', Price={4}, CurrencyID='{5}', Description='{6}', Title='{7}', Seller='{8}', URL='{9}', subcategory='{10}' WHERE ItemID={11}""".format(
             db.escape_string(poller_type),
             db.escape_string(images),
             lastUpdate,
             db.escape_string(category),
             price,
             db.escape_string(currency),
             db.escape_string(description),
             db.escape_string(title),
             db.escape_string(seller),
             db.escape_string(url),
             db.escape_string(subcategory),
             sku
            )

#        print "{0} DEBUG: {1}".format(stamp(),sql_statement)
        cursor.execute(sql_statement)

        
print "{0} sync_ebay.py complete".format(stamp())
