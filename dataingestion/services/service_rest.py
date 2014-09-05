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
from dataingestion.services import (constants, ingestion_service, csv_generator,
                                    ingestion_manager, api_client, model,
                                    result_generator, user_config)

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
    logger.debug("Authentication GET.")
    try:
      accountuuid = user_config.get_user_config('accountuuid')
      apikey = user_config.get_user_config('apikey')
    except AttributeError:
      return json.dumps(False)

    try:
      ret = api_client.authenticate(accountuuid, apikey)
      return json.dumps(ret)
    except ClientException as ex:
      cherrypy.log.error(str(ex), __name__)
      raise JsonHTTPError(503, str(ex))
 
  def POST(self, accountuuid, apikey):
    """
    Post an authentication information pair <user, password>.
    Raises:
      JsonHTTPError 503: if the service is unavilable.
      JsonHTTPError 409: if the UUID/APIKey combination is incorrect.
    """
    logger.debug("Authentication POST: {0}, {1}".format(accountuuid, apikey))
    try:
      ret = api_client.authenticate(accountuuid, apikey)
    except ClientException as ex:
      cherrypy.log.error(str(ex), __name__)
      raise JsonHTTPError(503, 'iDigBio Service Currently Unavailable.')

    if ret:
      # Set the attributes.
      user_config.set_user_config('accountuuid', accountuuid)
      user_config.set_user_config('apikey', apikey)
    else:
      raise JsonHTTPError(409, 'Authentication combination incorrect.')


class UserConfig(object):
  exposed = True

  def GET(self, name):
    """
    Returns the user configuration value of a name.
    """
    logger.debug("UserConfig GET: {0}".format(name))
    try:
      return json.dumps(ingestion_service.get_user_config(name))
    except AttributeError:
      raise JsonHTTPError(404, 'Not such config option is found.')

  def POST(self, name, value):
    """
    Sets a user configuration name with a value.
    """
    logger.debug("UserConfig POST: {0}, {1}".format(name, value))
    ingestion_service.set_user_config(name, value)

  def DELETE(self):
    """
    Removes all the user configurations.
    """
    ingestion_service.rm_user_config()


class LastBatchInfo(object):
  exposed = True

  def GET(self):
    """
    Returns information about the last batch upload.
    TODO: Will be extended to allow querying info about any previous batches.
    """
    logger.debug("LastBatchInfo GET.")
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
       csvuploaded, finished) = ingestion_manager.get_progress()
      return json.dumps(
          dict(fatal_server_error=fatal_server_error,
               input_csv_error=input_csv_error, total=total,
               successes=successes, skips=skips, fails=fails,
               csvuploaded=csvuploaded,
               finished=finished))
    except IngestServiceException as ex:
      raise JsonHTTPError(409, str(ex))


class IngestionResult(object):
  exposed = True
  
  def GET(self):
    """
    Retures the result of the current upload batch. 
    """
    logger.debug("IngestionResult GET.")
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
    logger.debug("History GET: {0}".format(table_id))
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
    logger.debug("GenerateCSV POST (values ommited here).")
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
    logger.debug("CsvIngestionService GET.")
    return '<html><body>CSV ingestion Service is running.</body></html>'

  def POST(self, values=None):
    """
    Ingest csv data.
    """
    logger.debug("CsvIngestionService POST.")
    if values is None:
      return self._resume()
    else:
      dic = ast.literal_eval(values) # Parse the string to dictionary.
      return self._upload(dic)

  def _upload(self, values):
    try:
      ingestion_service.start_upload(values)
    except ValueError as ex:
      raise JsonHTTPError(409, str(ex))

  def _resume(self):
    try:
      ingestion_service.start_upload()
    except ValueError as ex:
      raise JsonHTTPError(409, str(ex)) 


class GenerateAllCsv(object):
  """
  Generate the output CSV files, and put them into a zip file.
  """
  exposed = True

  def GET(self, values):
    logger.debug("DownloadAllCsv GET.")
    try:
      dic = ast.literal_eval(values) # Parse the string to dictionary.
      path, error = result_generator.generateCSV(
          None, dic['target_path'])
      return json.dumps(dict(path=path, error=error))


    except IOError as ex:
      print "ERROR GenerateAllCsv"
      raise JsonHTTPError(409, str(ex))


class GenerateOutputCsv(object):
  """
  Generate the output CSV files, and put them into a zip file.
  """
  exposed = True

  def GET(self, values):
    logger.debug("GenerateOutputCsv GET.")
    try:
      dic = ast.literal_eval(values) # Parse the string to dictionary.
      path, error = result_generator.generateCSV(
          dic['batch_id'], dic['target_path'])
      return json.dumps(dict(path=path, error=error))

    except IngestServiceException as ex:
      print "ERROR GenerateOutputCsv"
      raise JsonHTTPError(409, str(ex))


class GenerateOutputZip(object):
  """
  Generate the output CSV files, and put them into a zip file.
  """
  exposed = True

  def GET(self, values):
    logger.debug("GenerateOutputZip GET.")
    try:
      dic = ast.literal_eval(values) # Parse the string to dictionary.
      return json.dumps(
          result_generator.generateZip(dic['batch_id'], dic['target_path']))

    except IOError as ex:
      print "ERROR GenerateOutputZip"
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
    self.genoutputcsv = GenerateOutputCsv()
    self.genoutputzip = GenerateOutputZip()
    self.generateallcsv = GenerateAllCsv()
