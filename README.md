This is a project to transcribe items from amazon and ebay apis to a mysql database

pre-requirements

 AWS Account (Amazon) 
 Amazon Associate Account
 PA API is enabled for Associate Account (Product Advertising API key)
 eBay Developer API (Production or Developer Key) 
 python 2.7.x

To setup)

1) git clone (this repo)

2) Python 2.7.x is required (python-mysqldb requirement

3) install python-mysqldb

4) edit db.conf contains information about your database and must be updated to show current information

5) edit database.sql contains the skeleton of the database. It must be updated with the proper keys and then imported to  your mysql server.

mysql < database.sql (check this)

6) edit searches, and import as needed (direct updates work as well.) Two searches are included in the database, add more to the searches table to enable more searches.

7) run the search scripts (running the search python scripts), the available data will be in the sync table.

$ebay_search.py

$amazon_search.py


use cron to run these as regularly as needed.
