# Request mix-in classes

This directory contains mix-in classes to support the common types of web sites
for ETL scraping.

* HTML supported by `html.py`
* JSON supported by `json.py`
* XML supported by `xml.py`
* (soon selenium, but as a sub-class in parent directory)

The idea is that each of these classes provides a `request()` member function
that can be slotted into a `BaseScraper` sub-class such that it provides a
service to connect to a remote host, grab its data, and package it in a 
consistent way.  Usually the package will be a BeautifulSoup object, but for
JSON sites, we just return the JSON object for parsing.

