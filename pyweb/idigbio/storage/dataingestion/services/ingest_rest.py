#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

from idigbio.storage.dataingestion.services import ingest_service
#from idigbio.storage.dataingestion.services import mock_ingest_svc as ingest_service
import cherrypy, simplejson

class DataIngestionService(object):
    """
    The web service exposed through CherryPy.
    """
    exposed = True
    
    def __init__(self):
        pass
    
    def GET(self):
        """
        Get ingestion status.
        """
        total, remaining = ingest_service.check_progress()
        return simplejson.dumps(dict(total=total, remaining=remaining))
    
    def POST(self, rootPath):
        """
        Ingest data.
        """
        cherrypy.log.error("POST request received.", self.__class__.__name__)
        ingest_service.start_upload(rootPath)