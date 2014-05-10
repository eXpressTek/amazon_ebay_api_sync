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
cursor.execute("SELECT * FROM sync_config WHERE Sync_Type LIKE \"ebay\"")

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
cursor.execute("SELECT * FROM sync_searches WHERE search_poller LIKE \"ebay\"")

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
        seller = None
        images = item['galleryURL']['value']
        lastUpdate = time.time()
        subcategory = None
        category = item['primaryCategory']['categoryName']['value']
        price = item['sellingStatus']['currentPrice']['value']
        currency = item['sellingStatus']['currentPrice']['currencyId']['value']
        description = None
        title = item['title']['value']
        url = item['viewItemURL']['value']
        raw = item
        
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

        
print "{0} ebay_sync.py complete".format(stamp())
