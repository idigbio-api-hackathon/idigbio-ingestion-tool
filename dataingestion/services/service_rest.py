#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of
# Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

import cherrypy, json, logging, ast
from dataingestion.services.ingestion_manager import IngestServiceException
from cherrypy import HTTPError
from cherrypy._cpcompat import ntob
from dataingestion.services import (constants, ingest_service, csv_generator,
                                    ingestion_manager, api_client, model)

logger = logging.getLogger('iDigBioSvc.ingest_rest')


class JsonHTTPError(HTTPError):
  def set_response(self):
    cherrypy.response.status = self.status
    cherrypy.response.headers['Content-Type'] = "text/html;charset=utf-8"
    cherrypy.response.headers.pop('Content-Length', None)
    cherrypy.response.body = ntob(self._message)


class Authentication(object):
  exposed = True

  def GET(self):
    """
    Authenticate the user account and return the authentication result.
    """
    try:
      print("Authenticating ...")
      ret = ingest_service.authenticated()
      return json.dumps(ret)
    except Exception as ex:
      cherrypy.log.error('ingest_rest.Authentication:')
      cherrypy.log.error(str(ex), __name__)
      raise JsonHTTPError(503, 'iDigBio Service Currently Unavailable.')
 
  def POST(self, user, password):
    """
    Post an authentication information pair <user, password>.
    """
    try:
      ingest_service.authenticate(user, password)
    except ValueError:
      raise JsonHTTPError(409, 'Authentication combination incorrect.')
    except Exception as ex:
      cherrypy.log.error(str(ex), __name__)
      raise JsonHTTPError(503, 'iDigBio Service Currently Unavailable.')


class UserConfig(object):
  exposed = True

  def GET(self, name):
    """
    Returns the user configuration value of a name.
    """
    try:
      return json.dumps(ingest_service.get_user_config(name))
    except AttributeError:
      raise JsonHTTPError(404, 'Not such config option is found.')

  def POST(self, name, value):
    """
    Sets a user configuration name with a value.
    """
    ingest_service.set_user_config(name, value)

  def DELETE(self):
    """
    Removes all the user configurations.
    """
    ingest_service.rm_user_config()


class LastBatchInfo(object):
  exposed = True

  def GET(self):
    """
    Returns information about the last batch upload.
    TODO: Will be extended to allow querying info about any previous batches.
    """
    try:
      result = model.get_last_batch_info()
      return json.dumps(result)
    except IngestServiceException as ex:
      raise JsonHTTPError(409, str(ex))


class IngestionProgress(object):
  exposed = True

  def GET(self, **params):
    """
    Get ingestion status.
    """
    # **params added by Kyuho in July 23rd 2013 
    # It is required to accept dummy parameters. 
    # These dummy parameters requires to disable internet explorer browser
    # cache. Internet explorer does execute $.get when the url is the same for
    # the time being. 
    try:
      (fatal_server_error, input_csv_error, total, skips, successes, fails,
       finished) = ingestion_manager.get_progress()   
      return json.dumps(
          dict(fatal_server_error=fatal_server_error,
               input_csv_error=input_csv_error, total=total,
               successes=successes, skips=skips, fails=fails,
               finished=finished))
    except IngestServiceException as ex:
      raise JsonHTTPError(409, str(ex))


class IngestionResult(object):
  exposed = True
  
  def GET(self):
    """
    Retures the result of the current upload batch. 
    """
    try:
      result = ingestion_manager.get_result()
      resultdump = json.dumps(result)
      return resultdump
    except IngestServiceException as ex:
      raise JsonHTTPError(409, str(ex))


class History(object):
  exposed = True
  
  def GET(self, table_id):
    """
    Get the history of batches or images (depends on table_id).
    """
    try:
      result = ingestion_manager.get_history(table_id)
      resultdump = json.dumps(result)
      return resultdump
    except IngestServiceException as ex:
      raise JsonHTTPError(409, str(ex))


class GenerateCSV(object):
  exposed = True
  def POST(self, values):
    """
    Post a generate CSV request with the given values.
    """
    try:
      dic = ast.literal_eval(values) # Parse the string to dictionary.
      csv_generator.run_gencsv(dic)
    except IngestServiceException as ex:
      pass # Do not process it, as it can be captured by CSVGenProgress.


class CSVGenProgress(object):
  exposed = True

  def GET(self):
    """
    Get the CSV Generation status.
    """
    try:
      count, result, targetfile, error = csv_generator.check_progress()
      return json.dumps(dict(count=count, result=result, targetfile=targetfile,
                             error=error))
    except IngestServiceException as ex:
      raise JsonHTTPError(409, str(ex))


class CsvIngestionService(object):
  exposed = True

  def GET(self):
    return '<html><body>CSV ingestion Service is running.</body></html>'

  def POST(self, values=None):
    """
    Ingest csv data.
    """
    if values is None:
      return self._resume()
    else:
      dic = ast.literal_eval(values) # Parse the string to dictionary.
      return self._upload(dic)

  def _upload(self, values):
    try:
      ingest_service.start_upload(values)
    except ValueError as ex:
      raise JsonHTTPError(409, str(ex))

  def _resume(self):
    try:
      ingest_service.start_upload()
    except ValueError as ex:
      raise JsonHTTPError(409, str(ex)) 


class DataIngestionService(object):
  """
  The root RESTful web service exposed through CherryPy at /services
  """
  exposed = True

  def __init__(self):
    """
    Each self.{attr} manages the request to URL path /services/{attr}.
    """
    self.auth = Authentication()
    self.config = UserConfig()
    self.lastbatchinfo = LastBatchInfo()
    self.ingest = CsvIngestionService()
    self.ingestionprogress = IngestionProgress()
    self.ingestionresult = IngestionResult()
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
    try:
      if rootPath is None:
        return ingest_service.start_resume(constants.DIR_TYPE)
      else:
        return ingest_service.start_upload(rootPath, constants.DIR_TYPE)
    except ValueError as ex:
      raise JsonHTTPError(409, str(ex))
