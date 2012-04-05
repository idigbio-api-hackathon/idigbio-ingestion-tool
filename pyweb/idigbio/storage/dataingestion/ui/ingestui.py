#!/usr/bin/env python
#
# Copyright (c) 2011 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php 

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('www/templates/sandstorm'))

class DataIngestionResource(object):
    exposed = True
    def GET(self):
        tmpl = env.get_template('index.html')
        page_description = """
        Upload data from this page.
        """
        return tmpl.render(title='Data Ingestion', description=page_description)

class DataIngestionUI(object):
    exposed = True
    
    def __init__(self):
        self.ingest = DataIngestionResource()
    
    def GET(self):
        tmpl = env.get_template('index.html')
        page_description = """
        This is iDigBio Data Ingestion Tool, a tool to ingest data into the Swift data cloud.
        """
        return tmpl.render(title='Homepage', description=page_description)
