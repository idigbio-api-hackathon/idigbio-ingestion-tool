#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module encapulates the communication with iDigBio's storage service API.
"""
import argparse, json, urllib2, logging
import uuid
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers

BASE_URL = 'http://dev.idigbio.org:9191/v1'

logger = logging.getLogger("iDigBioSvc.apiclient")

register_openers()

def create_url(resource, guid=None, subresource=None):
    if guid is None:
        ret = "%s/%s/" % (BASE_URL, resource)
    elif subresource is None:
        ret = "%s/%s/%s/" % (BASE_URL, resource, guid)
    else:
        ret = "%s/%s/%s/%s/" % (BASE_URL, resource, guid, subresource)
    
    logger.debug("URL: %s" % ret)
    return ret


def _get_recordset_uuid():
    data = { "idigbio:data": { "ac:variant": "IngestionTool" },
            "idigbio:providerId": str(uuid.uuid4()) }
    url = create_url("recordsets")
    response = _post_json(url, data)
    logger.debug(response)
    return response['idigbio:uuid']

def _get_mediarecord_uuid(parent_uuid):
    data = { "idigbio:data": { "ac:variant": "IngestionTool" },
            "idigbio:providerId": str(uuid.uuid4()),
            "idigbio:parentUuid": parent_uuid }
    url = create_url("mediarecords")
    response = _post_json(url, data)
    logger.debug(response)
    return response['idigbio:uuid']

def _post_image(path, uuid):
    url = create_url("mediarecords", uuid, "media")
    datagen, headers = multipart_encode({"file": open(path, "rb")})
    request = urllib2.Request(url, datagen, headers)
    resp = urllib2.urlopen(request).read()
    logger.debug(resp)
    return json.loads(resp)


def _post_json(url, obj):
    """
    Returns reponse JSON object.
    """
    jo = json.dumps(obj, separators=(',',':'))
    req = urllib2.Request(url, jo, {'Content-Type': 'application/json'})  
    r = urllib2.urlopen(req)
    resp = r.read()
    json_response = json.loads(resp)
    return json_response

def upload_image(path):
    try:
        set_uuid = _get_recordset_uuid()
        mediarecord_uuid = _get_mediarecord_uuid(set_uuid)
        resp_json = _post_image(path, mediarecord_uuid)
        img_url = resp_json['idigbio:links']['media']
        return img_url
    except urllib2.HTTPError as e:
        logger.error("Upload failed: {0}".format(e))
        logger.error("Error headers: {0}".format(e.headers))
        raise Exception(e)
        

class ClientException(Exception):

    def __init__(self, msg, http_scheme='', http_host='', http_port='',
                 http_path='', http_query='', http_status=0, http_reason='',
                 http_device='', http_response_content=''):
        Exception.__init__(self, msg)
        self.msg = msg
        self.http_scheme = http_scheme
        self.http_host = http_host
        self.http_port = http_port
        self.http_path = http_path
        self.http_query = http_query
        self.http_status = http_status
        self.http_reason = http_reason
        self.http_device = http_device
        self.http_response_content = http_response_content

    def __str__(self):
        a = self.msg
        b = ''
        if self.http_scheme:
            b += '%s://' % self.http_scheme
        if self.http_host:
            b += self.http_host
        if self.http_port:
            b += ':%s' % self.http_port
        if self.http_path:
            b += self.http_path
        if self.http_query:
            b += '?%s' % self.http_query
        if self.http_status:
            if b:
                b = '%s %s' % (b, self.http_status)
            else:
                b = str(self.http_status)
        if self.http_reason:
            if b:
                b = '%s %s' % (b, self.http_reason)
            else:
                b = '- %s' % self.http_reason
        if self.http_device:
            if b:
                b = '%s: device %s' % (b, self.http_device)
            else:
                b = 'device %s' % self.http_device
        if self.http_response_content:
            if len(self.http_response_content) <= 60:
                b += '   %s' % self.http_response_content
            else:
                b += '  [first 60 chars of response] %s' % \
                   self.http_response_content[:60]
        return b and '%s: %s' % (a, b) or a


def main():
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path")
    args = parser.parse_args()
    img_url = upload_image(args.image_path)
    logger.info("URL for the uploaded image: {0}".format(img_url))
    
if __name__ == '__main__':
    main()