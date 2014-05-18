This is a project to transcribe items from amazon and ebay apis to a mysql database

pre-requirements

 AWS Account (Amazon) 
 Amazon Associate Account
 PA API is enabled for Associate Account (Product Advertising API key)
 eBay Developer API (Production or Developer Key) 
 python 2.7.x

To setup)

1) git clone (this repo)

2) Python 2.7.x is required (python-mysqldb requirement)

3) install python-mysqldb
   install lxml

4) cp db.conf-template to db.conf and edit
  contains information about your database and must be updated to show current information

5) cp database.sql-template database.sql
 contains the skeleton of the database. It must be updated with the proper keys and then imported to  your mysql server.
 you may also use this as a reference to update your db as needed

  mysql -u username -p -h localhost DATA-BASE-NAME < data.sql

6) edit searches, and import as needed (direct updates work as well.) Two searches are included in the database, add more to the searches table to enable more searches.

7) run the search scripts (running the search python scripts), the available data will be in the sync table.

$PATH/python sync_ebay.py
$PATH/python sync_amazon.py

use cron to run these as regularly as needed.




nice to haves!
______________
 we recommend myPHPAdmin loaded on your development server (if you don't already have a graphical editor for the DB)
 A nice tutorial to set it up (in minutes) on CentOS using the epel library can be found here -> https://www.digitalocean.com/community/articles/how-to-install-and-secure-phpmyadmin-on-a-centos-6-4-vps

 basic steps are: 
  cd ~
  wget http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
  sudo rpm -ivh epel-release*
  rm epel-release*
  yum install phpmyadmin
  /etc/httpd/conf.d/phpMyAdmin.conf (add your IP's you want to administer the database from)
  service httpd start
  point your web browser at the console http://<your_ip>/phpmyadmin
  enjoy

