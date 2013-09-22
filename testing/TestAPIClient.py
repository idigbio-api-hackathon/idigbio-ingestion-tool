#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distribted according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

# This preprocess is to set up the paths to make sure the current module
# referencing in the files to be tested.
import sys, os, unittest, tempfile, datetime
rootdir = os.path.dirname(os.getcwd())
sys.path.append(rootdir)
sys.path.append(os.path.join(rootdir, 'lib'))

from dataingestion.services import api_client

class TestAPIClient(unittest.TestCase):
  def setUp(self):
    self._endpoint = "http://beta-api.idigbio.org/v1"
    api_client.init(self._endpoint)
    # The following uuid/apikey pair is only for testing purpose.
    self._accountuuid = "60f7cb1e-02f5-425c-bc37-cae87550317a"
    self._apikey = "99f3ea05d8229a2f0d3aa1fcadf4a9a3"
    # Make the media file paths.
    self._filepath = os.path.join(os.getcwd(), "image1.jpg")
    self._invalidfilepath = "Notvalid/path.jpg"

  def _testBuildUrl(self):
    '''Test _build_url with different parameters.'''
    self.assertEqual(api_client._build_url("recordsets"),
                     "http://beta-api.idigbio.org/v1/recordsets")
    self.assertEqual(api_client._build_url("recordsets", "ABCDEFG"),
                     "http://beta-api.idigbio.org/v1/recordsets/ABCDEFG")
    self.assertEqual(api_client._build_url("recordsets", "A", "123456"),
                     "http://beta-api.idigbio.org/v1/recordsets/A/123456")

  def _testAuthenticate(self):
    '''
    Test the authenticate function. It is also prerequisit for following tests.
    '''
    self.assertTrue(api_client.authenticate(self._accountuuid, self._apikey))

    api_client.auth_string = None # Reset auth_string to remove the state.
    self.assertFalse(
        api_client.authenticate("60f7cb1e-02f5-425c-bc37-thisiswrongid",
                                self._apikey))

  def _testPostRecordset(self):
    '''Test _post_recordset, varify it can return correct information.'''

    # Authenticate first.
    self.assertTrue(api_client.authenticate(self._accountuuid, self._apikey))

    recordset_id1 = "test1"
    metadata1 = {"idigbio:RightsLicense": "CC0",
                 "idigbio:iDigbioProvidedByGUID": self._accountuuid,
                 "idigbio:RecordSetGUID": recordset_id1,
                 "idigbio:CSVfilePath": "/tmp/CSVfile1.csv"}
    self._recordset_uuid1 = api_client._post_recordset(recordset_id1, metadata1)

    recordset_id2 = "test2"
    metadata2 = {"idigbio:RightsLicense": "CC BY-SA",
                 "idigbio:iDigbioProvidedByGUID": self._accountuuid,
                 "idigbio:RecordSetGUID": recordset_id2,
                 "idigbio:CSVfilePath": "/tmp/CSVfile2.csv",
                 "idigbio:MediaContentKeyword": "kw1, kw2, kw3",
                 "idigbio:iDigbioProviderGUID": "providerGUID",
                 "idigbio:FundingSource": "NSF",
                 "idigbio:FundingPurpose": "The funding purpose."}
    self._recordset_uuid2 = api_client._post_recordset(recordset_id2, metadata2)
    # The dataset_uuids of the two uploads should be different, as they are
    # hashed from different provider_ids.
    self.assertNotEqual(self._recordset_uuid1, self._recordset_uuid2)

  def _testPostMediarecord(self):
    '''Test _post_mediarecord.'''
    media_id1 = "test1/f1"
    metadata1 = {
        "xmpRights:usageTerms": "CC0",
        "xmpRights:webStatement":
        "http://creativecommons.org/publicdomain/zero/1.0/",
        "ac:licenseLogoURL":
        "http://mirrors.creativecommons.org/presskit/buttons/80x15/png" + 
        "/publicdomain.png",
        "idigbio:MimeType": "image/jpeg"}
    self._record_uuid1, self._mr_etag1, self._mr_str1 = \
        api_client._post_mediarecord(self._recordset_uuid1, self._filepath,
                                     media_id1, metadata1)
    self.assertIsNotNone(self._record_uuid1)
    self.assertIsNotNone(self._mr_etag1)
    self.assertIsNotNone(self._mr_str1)

    media_id2 = "test2/f2"
    metadata2 = {
        "xmpRights:usageTerms": "CC BY-SA",
        "xmpRights:webStatement":
        "http://creativecommons.org/licenses/by-sa/3.0/",
        "ac:licenseLogoURL":
        "http://mirrors.creativecommons.org/presskit/buttons/80x15/png" + 
        "/by-sa.png",
        "idigbio:MimeType": "image/jpeg",
        "Annotaions": "{'idigbio:Description': 'Some description.'," +
                      "'idigbio:LanguageCode': 'French'," +
                      "'idigbio:Title': 'Some title'," +
                      "'idigbio:DigitalizationDevice': 'Dig device.'}"}
    self._record_uuid2, self._mr_etag2, self._mr_str2 = \
        api_client._post_mediarecord(self._recordset_uuid2,
                                     self._invalidfilepath, media_id2,
                                     metadata2)
    self.assertIsNotNone(self._record_uuid2)
    self.assertIsNotNone(self._mr_etag2)
    self.assertIsNotNone(self._mr_str2)

  def _testPostMedia(self):
    '''Test _post_media.'''
    # The file exists.
    api_client._post_media(self._filepath, self._record_uuid1)
    # The path does not exist.
    self.assertRaises(IOError, api_client._post_media, self._invalidfilepath,
                      self._record_uuid2)
    # The path is a directory.
    self.assertRaises(IOError, api_client._post_media, os.getcwd(),
                      self._record_uuid2)

  def _testConnection(self):
    '''
    Test the connection with authenticate, .
    '''
    conn = api_client.Connection() 
    recordset_id = "testConnection"
    metadata = {"idigbio:RightsLicense": "CC0",
                "idigbio:iDigbioProvidedByGUID": self._accountuuid,
                "idigbio:RecordSetGUID": recordset_id,
                "idigbio:CSVfilePath": "/tmp/CSVfile1.csv"}
    self._recordset_uuid = conn.post_recordset(recordset_id, metadata)

  def runTest(self):
    self._testBuildUrl()
    self._testAuthenticate()
    self._testPostRecordset()
    self._testPostMediarecord()
    self._testPostMedia()
    self._testConnection()


if __name__ == '__main__':
      unittest.main()
