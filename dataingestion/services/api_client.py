#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module encapulates the communication with iDigBio's storage service API.
"""
import cherrypy
import socket
import argparse, json, urllib2, logging
import uuid
import base64
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from time import sleep
from httplib import HTTPException

logger = logging.getLogger("iDigBioSvc.api_client")
register_openers()

api_endpoint = None

def init(api_ep):
  global api_endpoint
  api_endpoint = api_ep

TIMEOUT = 5

def _build_url(collection, entity_uuid=None, subcollection=None):
  assert api_endpoint

  if entity_uuid is None:
    ape = api_endpoint
    if collection == "check":
      ape = "/".join(api_endpoint.split("/")[:-1])
    ret = "%s/%s" % (ape, collection)
  elif subcollection is None:
    ret = "%s/%s/%s" % (api_endpoint, collection, entity_uuid)
  else:
    ret = "%s/%s/%s/%s" % (api_endpoint, collection, entity_uuid, subcollection)
  return ret

def _post_recordset(recordset_id, metadata):
  data = {"idigbio:data": {"ac:variant": "IngestionTool"},
          "idigbio:recordIds": [recordset_id]}
  data["idigbio:data"] = dict(data["idigbio:data"].items() + metadata.items())

  url = _build_url("recordsets")
  logger.debug("POSTing recordset...")
  try:
    response = json.loads(_post_json(url, data))
    logger.debug("POSTing recordset done.")
  except urllib2.HTTPError as e:
    logger.error("Failed to POST the recordset to server.")
    raise ClientException("Failed to POST the recordset to server.", url=url,
                          http_status=e.code, http_response_content=e.read(),
                          reason=recordset_id)
  except (urllib2.URLError, socket.error, HTTPException) as e:
    logger.error("{0} caught while POSTing the recordset.".format(type(e)))
    raise ClientException(
        "{0} caught while POSTing the recordset.".format(type(e)),
        reason=str(e), url=url)
  except (IOError, OSError) as e:
    logger.error("IOError or OSError.")
    raise ClientException("IOError caught.")
  return response['idigbio:uuid']

def _post_mediarecord(recordset_uuid, path, media_id, specimen_uuid, idigbio_metadata):
  '''
  Returns the UUID of the Media Record and the raw MR JSON String as a tuple.
  '''
  logger.debug('_post_mediarecord')
  logger.debug('idigbio_metadata: {0}'.format(idigbio_metadata))

  data = {
      "idigbio:data": {
          "ac:variant": "IngestionTool",
          "idigbio:OriginalFileName": path,
          "idigbio:MediaGUID": media_id,
          "idigbio:relationships": {"recordset": recordset_uuid}},
      "idigbio:recordIds": [media_id]}
  if specimen_uuid is not "":
    data["idigbio:data"]["idigbio:relationships"]["record"] = specimen_uuid
  data["idigbio:data"] = dict(data["idigbio:data"].items() +
                              idigbio_metadata.items())

  logger.debug('_post_mediarecord data:{0}'.format(data)) #QHO
  url = _build_url("mediarecords")
  logger.debug("POSTing mediarecord...")
  try:
    resp1 = _post_json(url, data)
    response = json.loads(resp1)
    logger.debug("POSTing mediarecord done.")
  except urllib2.HTTPError as e:
    raise ClientException("Failed to POST the mediarecord to server.", url=url,
                          http_status=e.code, http_response_content=e.read(),
                          reason=recordset_uuid)
  except (urllib2.URLError, socket.error, HTTPException) as e:
    raise ClientException(
        "{0} caught while POSTing the mediarecord.".format(type(e)),
        reason=str(e), url=url)
  return response['idigbio:uuid'], response['idigbio:etag'], resp1

def _post_media(local_path, entity_uuid):
  '''
  Returns the JSON String of the Media AP.
  Exceptions:
    IOError: If the local path is not a valid file.
    ClientException: If
  '''
  url = _build_url("mediarecords", entity_uuid, "media")
  logger.debug("POSTing media...")
  datagen, headers = multipart_encode({"file": open(local_path, "rb")})
  try:
    request = urllib2.Request(url, datagen, headers)
    request.add_header("Authorization", "Basic %s" % auth_string)
    resp = urllib2.urlopen(request, timeout=TIMEOUT).read()
    logger.debug("POSTing media done.")
    return resp
  except urllib2.HTTPError as e:
    logger.debug("urllib2.HTTPError caught")
    logger.debug("Error code {0}".format(e.code))
    if e.code == 500:
      logger.debug("ServerException occurs")
      raise ServerException(
          "Fatal Server Exception Detected. HTTP Error code:{0}".format(e.code))
    raise ClientException(
        "Failed to POST the media to server", url=request.get_full_url(),
        http_status=e.code, http_response_content=e.read(), reason=entity_uuid,
        local_path=local_path)
  except (urllib2.URLError, socket.error, HTTPException) as e:
    raise ClientException("{0} caught while POSTing the media.".format(type(e)),
                          reason=str(e), url=url)

# Post the request to the server and get the response.
def _post_json(url, obj):
  """
  Returns: the reponse JSON object.
  """
  content = json.dumps(obj, separators=(',',':'))
  logger.debug("content -> " + str(content))
  req = urllib2.Request(url, content, {'Content-Type': 'application/json'})

  req.add_header("Authorization", "Basic %s" % auth_string)
  r = urllib2.urlopen(req, timeout=TIMEOUT)
  resp = r.read()
  return resp

auth_string = None

def authenticate(user, key):
  """
  Connect with the server to authenticate the accountID/key pair.
  Params:
    user: user account ID.
    key: The API key for the account ID.
  Returns:
    True if authentication is successful.
    False if authentication fails due to incorrect accountID/key pair.
  Except:
    ClientException: if the network connection corrupts or the server side is
                     unavailable.
  """

  global auth_string
  if auth_string: # This means the authentication was already successful.
    return True
  url = _build_url('check')
  try:
    req = urllib2.Request(url, '{ "idigbio:data": { } }',
                          {'Content-Type': 'application/json'})
    base64string = base64.encodestring('%s:%s' % (user, key)).replace('\n', '')
    req.add_header("Authorization", "Basic %s" % base64string)
    urllib2.urlopen(req, timeout=10)
    logger.debug("Successfully logged in.")
    auth_string = base64string
    return True
  except urllib2.HTTPError as e:
    if e.code == 403:
      logger.error(str(e))
      return False
    else:
      raise ClientException("Failed to authenticate with server.", url=url,
                            http_status=e.code, http_response_content=e.read(),
                            reason=user)

class ClientException(Exception):
  def __init__(self, msg, url='', http_status=None, reason='', local_path='',
         http_response_content=''):
    Exception.__init__(self, msg)
    self.msg = msg
    self.url = url
    self.http_status = http_status
    self.reason = reason
    self.local_path = local_path
    self.http_response_content = http_response_content

  def __str__(self):
    a = self.msg
    b = ''
    if self.url:
      b += self.url
    if self.http_status:
      if b:
        b = '%s %s' % (b, self.http_status)
      else:
        b = str(self.http_status)
    if self.reason:
      if b:
        b = '%s %s' % (b, self.reason)
      else:
        b = '- %s' % self.reason
    if self.local_path:
      if b:
        b = '%s %s' % (b, self.local_path)
      else:
        b = '- %s' % self.local_path
    if self.http_response_content:
      if len(self.http_response_content) <= 200:
        b += '   %s' % self.http_response_content
      else:
        b += '  [first 60 chars of response] %s' % \
           self.http_response_content[:200]
    return b and '%s: %s' % (a, b) or a


"""
This class is for Fatal Server Failure at server side.
If permanent server failure occurs, the appliance should elegantly finish itself.
Added by Kyuho on 06/17/2013
"""
class ServerException(Exception):
  def __init__(self, msg, http_status=None):
    Exception.__init__(self, msg)
    self.msg = msg
    self.http_status = http_status

  def __str__(self):
    return self.msg + str(self.http_status)


class Connection(object):
  """Convenience class to make requests that will also retry the request"""

  def __init__(self, authurl=None, user=None, key=None, retries=8,
               preauthurl=None, preauthtoken=None, snet=False,
               starting_backoff=1, auth_version="1"):
    """
    Params:
      authurl: authenitcation URL
      user: user name to authenticate as
      key: key/password to authenticate with
      retries: Number of times to retry the request before failing
      preauthurl: storage URL (if you have already authenticated)
      preauthtoken: authentication token (if you have already authenticated)
      snet: use SERVICENET internal network default is False
      auth_version: Openstack auth version.
    """
    self.authurl = authurl
    self.user = user
    self.key = key
    self.retries = retries
    self.http_conn = None
    self.url = preauthurl
    self.token = preauthtoken
    self.attempts = 0
    self.snet = snet
    self.starting_backoff = starting_backoff
    self.auth_version = auth_version

  def _retry(self, reset_func, func, *args, **kwargs):
    self.attempts = 0
    backoff = self.starting_backoff
    while self.attempts <= self.retries:
      self.attempts += 1
      try:
        rv = func(*args, **kwargs)
        return rv
      except ClientException as err:
        logger.debug("ClientException caught: {0}".format(err))
        logger.debug("Current retry attempts: {0}".format(self.attempts))

        if self.attempts > self.retries:
          logger.debug("Retries exhausted.")
          raise

        if err.http_status == 401: # Unauthorized
          if self.attempts > 1:
            raise
        elif err.http_status == 408: # Request Timeout
          pass
        elif 500 <= err.http_status <= 599:
          pass
        elif err.http_status is None:
          pass
        else:
          raise

      sleep(backoff)
      backoff *= 2
      if reset_func:
        reset_func(func, *args, **kwargs)

  def post_recordset(self, recordset_id, metadata):
    return self._retry(None, _post_recordset, recordset_id, metadata)

  def post_mediarecord(self, recordset_uuid, path, media_id, specimen_uuid,
                       idigbio_metadata):
    return self._retry(None, _post_mediarecord, recordset_uuid, path,
                       media_id, specimen_uuid, idigbio_metadata)

  def post_media(self, local_path, entity_uuid):
    return self._retry(None, _post_media, local_path, entity_uuid)
