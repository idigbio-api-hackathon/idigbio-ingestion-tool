#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

#from dataingestion.services import mock_ingest_svc as ingest_service
import cherrypy, json, logging, ast
from dataingestion.services.ingestion_manager import IngestServiceException
from cherrypy import HTTPError
from cherrypy._cpcompat import ntob
from dataingestion.services import constants, ingest_service, csv_generator

logger = logging.getLogger('iDigBioSvc.ingest_rest')

class JsonHTTPError(HTTPError):
    def set_response(self):
        cherrypy.response.status = self.status
        cherrypy.response.headers['Content-Type'] = "text/html;charset=utf-8"
        cherrypy.response.headers.pop('Content-Length', None)
        cherrypy.response.body = ntob(self._message)

class BatchInfo(object):
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
            raise JsonHTTPError(409, str(ex))

class IngestionResult(object):
    '''
    REST resource that represents the result of an upload batch. 
    '''
    exposed = True
    def GET(self):
        try:
            result = ingest_service.get_result()
            resultdump = json.dumps(result)
            return resultdump
        except IngestServiceException as ex:
            raise JsonHTTPError(409, str(ex))

class UserConfig(object):
    '''
    REST resource that represents the user config.
    '''
    exposed = True
    def GET(self, name):
        try:
            return json.dumps(ingest_service.get_user_config(name))
        except AttributeError:
            raise JsonHTTPError(404, 'Not such config option is found.')

    def POST(self, name, value):
        ingest_service.set_user_config(name, value)

    def DELETE(self):
        ingest_service.rm_user_config()

class History(object):
    '''
    Get the history of batches or images.
    '''
    exposed = True
    def GET(self, table_id):
        try:
            result = ingest_service.get_history(table_id)
            resultdump = json.dumps(result)
            return resultdump
        except IngestServiceException as ex:
            raise JsonHTTPError(409, str(ex))

class GenerateCSV(object):
    exposed = True
    def POST(self, values):
        try:
            dic = ast.literal_eval(values) # Parse the string to dictionary.
            csv_generator.run_gencsv(dic)
        except IngestServiceException as ex:
            pass # Do not process it, as the exception can be captured by CSVGenProgress.

class Authentication(object):
    '''
    REST resource that signs in the user.
    '''
    exposed = True
    def GET(self):
        try:
            print("Authenticating ...")
            ret = ingest_service.authenticated()
            return json.dumps(ret)
        except Exception as ex:
            cherrypy.log.error('ingest_rest.Authentication:')
            cherrypy.log.error(str(ex), __name__)
            raise JsonHTTPError(503, 'iDigBio Service Currently Unavailable.')

    def POST(self, user, password):
        try:
            ingest_service.authenticate(user, password)
        except ValueError:
            raise JsonHTTPError(409, 'Authentication combination incorrect.')
        except Exception as ex:
            cherrypy.log.error(str(ex), __name__)
            raise JsonHTTPError(503, 'iDigBio Service Currently Unavailable.')
        
class ProgressStatus(object):
    exposed = True
    def GET(self):
        """
        Get ingestion status.
        """
        try:
            total, skips, successes, fails, finished = ingest_service.check_progress()
            return json.dumps(dict(total=total, successes=successes, 
                                   skips=skips, fails=fails, finished=finished))
        except IngestServiceException as ex:
            raise JsonHTTPError(409, str(ex))

class CSVGenProgress(object):
    exposed = True
    def GET(self):
        """
        Get CSV Generation status.
        """
        try:
            count, result, targetfile, error = csv_generator.check_progress()
            return json.dumps(dict(count=count, result=result, targetfile=targetfile,
            error=error))
        except IngestServiceException as ex:
            raise JsonHTTPError(409, str(ex))

class DataIngestionService(object):
    """
    The root RESTful web service exposed through CherryPy at /services
    """
    exposed = True
    def __init__(self):
        '''
        self.{attr} is answers the request to URL path /services/{attr}.
        '''
        self.result = IngestionResult()
        self.batch = BatchInfo()
        self.config = UserConfig()
        self.auth = Authentication()
        self.progress = ProgressStatus()
        self.csv = CsvIngestionService()
        self.history = History()
        self.generatecsv = GenerateCSV()
        self.csvgenprogress = CSVGenProgress()

    def GET(self):
        return '<html><body>Ingestion Service is running.</body></html>'

    def POST(self, rootPath=None):
        """
        Ingest data.
        """
        logger.debug("POST dir request received.", self.__class__.__name__)
        if rootPath is None:
            return self._resume()
        else:
            return self._upload(rootPath)

    def _upload(self, rootPath):
        try:
            ingest_service.start_upload(rootPath, constants.DIR_TYPE)
        except ValueError as ex:
            raise JsonHTTPError(409, str(ex))
    
    def _resume(self):
        try:
            ingest_service.start_resume(constants.DIR_TYPE)
        except ValueError as ex:
            raise JsonHTTPError(409, str(ex))


class CsvIngestionService(object):
    exposed = True
    def GET(self):
        return '<html><body>CSV ingestion Service is running.</body></html>'

    def POST(self, values=None):
        """
        Ingest csv data.
        """
#        logger.debug("POST csv request received.", self.__class__.__name__)
        if values is None:
            return self._resume()
        else:
            dic = ast.literal_eval(values) # Parse the string to dictionary.
            return self._upload(dic)

    def _upload(self, values):
        try:
            ingest_service.start_upload(values, constants.CSV_TYPE)
        except ValueError as ex:
            raise JsonHTTPError(409, str(ex))

    def _resume(self):
        try:
            ingest_service.start_resume(constants.CSV_TYPE)
        except ValueError as ex:
            raise JsonHTTPError(409, str(ex)) 