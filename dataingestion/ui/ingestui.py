#!/usr/bin/env python
#
# Copyright (c) 2011 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php 

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('www/'))

class DataIngestionUI(object):
    exposed = True
    
    def __init__(self):
        pass
    
    def GET(self):
        tmpl = env.get_template('index.html')
        title = "Data Ingestion Tool"
        page_description = """
        This is a tool that helps you ingest data into the iDigBio storage cloud.
        """
        return tmpl.render(title=title, description=page_description)
