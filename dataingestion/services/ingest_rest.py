#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

from dataingestion.services import ingest_service
#from dataingestion.services import mock_ingest_svc as ingest_service
import cherrypy, json
from dataingestion.services.ingestion_manager import IngestServiceException
from cherrypy import HTTPError
from cherrypy._cpcompat import ntob

class JsonHTTPError(HTTPError):
    def set_response(self):
        cherrypy.response.status = self.status
        cherrypy.response.headers['Content-Type'] = "text/html;charset=utf-8"
        cherrypy.response.headers.pop('Content-Length', None)
        cherrypy.response.body = ntob(self._message)

class BatchInfo():
    '''
    REST resource that represents info of a batch upload.
    '''
    
    exposed = True

    def GET(self):
        '''
        Currently only return info about the last batch.
        
        Will be extended to allow querying info about any previous batches. 
        '''
        try:
            result = ingest_service.get_last_batch_info()
            return json.dumps(result)
        except IngestServiceException as ex:
            raise cherrypy.HTTPError(409, str(ex))

class IngestionResult(object):
    '''
    REST resource that represents the result of an upload batch. 
    '''
    exposed = True

    def GET(self):
        try:
            result = ingest_service.get_result()
            return json.dumps(result)
        except IngestServiceException as ex:
            raise cherrypy.HTTPError(409, str(ex))

class DataIngestionService(object):
    """
    The RESTful web service exposed through CherryPy.
    """
    exposed = True

    def __init__(self):
        self.result = IngestionResult()
        self.batch = BatchInfo()

    def GET(self):
        """
        Get ingestion status.
        """
        try:
            total, remaining = ingest_service.check_progress()
            return json.dumps(dict(total=total, remaining=remaining))
        except IngestServiceException as ex:
            raise cherrypy.HTTPError(409, str(ex))

    def POST(self, rootPath):
        """
        Ingest data.
        """
        cherrypy.log.error("POST request received.", self.__class__.__name__)
        try:
            ingest_service.start_upload(rootPath)
        except ValueError as ex:
            raise JsonHTTPError(409, str(ex))
