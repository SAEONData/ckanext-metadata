#!/bin/bash
set -e

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty

echo "Installing CKAN v$CKAN_VERSION and its Python dependencies..."
wget https://github.com/ckan/ckan/archive/ckan-$CKAN_VERSION.tar.gz -O ckan.tar.gz
tar xzf ckan.tar.gz
mv ckan-ckan-$CKAN_VERSION ckan
cd ckan
pip install -e .
sed -i 's/psycopg2.*/psycopg2==2.7.3.2/' requirements.txt
pip install -r requirements.txt --allow-all-external
pip install -r dev-requirements.txt --allow-all-external
cd -

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Initialising SOLR..."
# Solr is multicore for tests on ckan master, but it's easier to run tests on
# Travis single-core. See https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini
echo -e "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty restart

echo "Checking that SOLR is up"
curl http://127.0.0.1:8983/solr/admin/ping

echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini
cd -

echo "Installing ckanext-metadata and its requirements..."
python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

echo "Installing ckanext-jsonpatch v$JSONPATCH_VERSION and its requirements..."
wget https://github.com/SAEONData/ckanext-jsonpatch/archive/v$JSONPATCH_VERSION.tar.gz -O ckanext-jsonpatch.tar.gz
tar xzf ckanext-jsonpatch.tar.gz
cd ckanext-jsonpatch-$JSONPATCH_VERSION
python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt

echo "travis-build.bash is done."