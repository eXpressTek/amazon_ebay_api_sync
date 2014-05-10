import bottlenose
import xmltodict
import xml.etree.ElementTree as ElementTree
import json
import MySQLdb
import credentials
import time
import sys

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
cursor.execute("SELECT * FROM sync_config WHERE Sync_Type LIKE \"Amazon\"")

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
cursor.execute("SELECT * FROM sync_searches WHERE search_poller LIKE \"amazon\"")

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
        
        #mappings for the database fields
        sku = itemInfo['ASIN']
        poller_type = "amazon"
        images = itemInfo['ImageSets']
        lastUpdate = time.time()
        category = itemInfo['ItemAttributes']['ProductGroup']
        subcategory = itemInfo['BrowseNodes']
        price = float(itemInfo['ItemAttributes']['ListPrice']['Amount'])/100
        currency = itemInfo['ItemAttributes']['ListPrice']['CurrencyCode']
        dirty_description = itemInfo['ItemAttributes']['Feature']
        description = []
        
        #sanitize the description
        for desc in description:
            desc = re.sub('\\', '', desc)
            description.append(desc)
        title = itemInfo['ItemAttributes']['Title']
        seller = itemInfo['ItemAttributes']['Publisher']
        url = itemInfo['DetailPageURL']
        raw = itemInfo
        
        #print progress of SKU's with timestamp
        print "{1} got_sku={0}".format(sku,stamp()),
        
        # check if its already in the database
        recordNum = cursor.execute("SELECT * FROM sync WHERE ItemID LIKE \"%s\"", (sku))

        # if its not in the database, INSERT the new record
        if (recordNum == 0L) or (recordNum == 0):
            print "sku doesnt exist INSERT'ing new entry"
            cursor.execute("INSERT INTO sync (ItemID, Type, Images, LastUpdate, SubCategory, Category, Price, CurrencyID, Description, Title, Seller, URL) VALUES (\"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", %s, \"%s\", \"%s\", \"%s\", \"%s\", \"%s\")",(sku, poller_type, images, lastUpdate, subcategory, category, price, currency, description, title, seller, url))

        # else its an existing record and we need to update
        else:
            print "sku does exist UPDATE'ing the EXISTING entry"
            cursor.execute("UPDATE sync SET ItemID=\"%s\", Type=\"%s\", Images=\"%s\", LastUpdate=\"%s\", SubCategory=\"%s\", Category=\"%s\", Price=%s, CurrencyID=\"%s\", Description=\"%s\", Title=\"%s\", Seller=\"%s\", URL=\"%s\" WHERE ItemID=%s",(sku, poller_type, images, lastUpdate, subcategory, category, price, currency, description, title, seller, url, sku))

        # make it sleep a tick before starting the next record to allow for rate-limiting behavior
        time.sleep(.5)

print "{0} ebay_sync.py complete".format(stamp())
