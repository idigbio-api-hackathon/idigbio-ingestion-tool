#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
from idigbio.storage.dataingestion.services import ingestmanager
import cherrypy, simplejson

class DataIngestionService(object):
    exposed = True
    
    def __init__(self):
        pass
    
    def GET(self):
        """
        Get ingestion status.
        """
        total, remaining = ingestmanager.check_progress()
        return simplejson.dumps(dict(total=total, remaining=remaining))
    
    def POST(self, rootPath):
        """
        Ingest data.
        """
        cherrypy.log("Post request received.")
        ingestmanager.start_upload(rootPath)