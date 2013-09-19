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

from dataingestion.services import (
    user_config, api_client, model, ingestion_manager)

class TestUserConfig(unittest.TestCase):
  def setUp(self):
    f = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    self._filePath = f.name
    f.close()

  def runTest(self):
    # Test setup, set_user_config and get_user_config.
    user_config.setup(self._filePath)
    name_values = {'account_uuid': 'id1', 'api_key': 'key1'}
    user_config.set_user_config('account_uuid', name_values['account_uuid'])
    user_config.set_user_config('api_key', name_values['api_key'])
    self.assertTrue(user_config.get_user_config('account_uuid'),
                    name_values['account_uuid'])
    self.assertTrue(user_config.get_user_config('api_key'),
                    name_values['api_key'])
    # Test rm_user_config and try_get_user_config.
    user_config.rm_user_config()
    self.assertIsNone(user_config.try_get_user_config('account_uuid'))


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

  def _testPostRecordset(self):
    '''Test _post_recordset, varify it can return correct information.'''

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

class TestModel(unittest.TestCase):
  def setUp(self):
    '''Set up a tmp db file for the testing.'''
    self._testDB = os.path.join(os.getcwd(), "idigbio.ingest_test.db")
    model.setup(self._testDB)

  def tearDown(self):
    '''Clean up the tmp db file.'''
    model.close()
    os.remove(self._testDB)

  def _validateBatchFields(
      self, batch, path, accountID, license, licenseStatementUrl,
      licenseLogoUrl, recordset_guid, recordset_uuid, keyword, proID, pubID,
      fundingSource, fundingPurpose):
    '''Validate a upload batch has the field values same as given.'''
    self.assertEqual(batch.CSVfilePath, path)
    self.assertEqual(batch.iDigbioProvidedByGUID, accountID)
    self.assertEqual(batch.RightsLicense, license)
    self.assertEqual(batch.RightsLicenseStatementUrl, licenseStatementUrl)
    self.assertEqual(batch.RightsLicenseLogoUrl, licenseLogoUrl)
    self.assertEqual(batch.RecordSetGUID, recordset_guid)
    self.assertEqual(batch.RecordSetUUID, recordset_uuid)
    self.assertIsNone(batch.finish_time)
    self.assertEqual(batch.MediaContentKeyword, keyword)
    self.assertEqual(batch.iDigbioProviderGUID, proID)
    self.assertEqual(batch.iDigbioPublisherGUID, pubID)
    self.assertEqual(batch.FundingSource, fundingSource)
    self.assertEqual(batch.FundingPurpose, fundingPurpose)

  def _validateImageRecordFields(
      self, record, filepath, mediaguid, error, warnings, mimetype, msize,
      annotations, batchID):
    '''Validate a image record has the field values same as given.'''
    self.assertEqual(record.OriginalFileName, filepath)
    self.assertEqual(record.MediaGUID, mediaguid)
    self.assertEqual(record.Error, error)
    self.assertEqual(record.Warnings, warnings)
    self.assertEqual(record.MimeType, mimetype)
    if record.MediaSizeInBytes and msize:
      self.assertEqual(int(record.MediaSizeInBytes), int(msize))
    else:
      self.assertEqual(record.MediaSizeInBytes, msize)
    self.assertEqual(record.Annotations, annotations)
    self.assertEqual(record.BatchID, batchID)
    # We do not validate the value of the following fields because they
    # may change or there is no need.
    self.assertIsNotNone(record.ProviderCreatedTimeStamp)
    self.assertIsNotNone(record.ProviderCreatedByGUID)
    self.assertIsNotNone(record.MediaEXIF)
    self.assertIsNotNone(record.MediaMD5)
    self.assertIsNotNone(record.AllMD5)

  def _testAddBatch(self):
    '''Test add_batch with various inputs.'''
    # The following fields will be reused.
    path = os.path.join(os.getcwd(), "image1.jpg")
    accountID = "accountID"
    license = "license"
    licenseStatementUrl = "licenseurl"
    licenseLogoUrl = "licenselogourl"
    recordset_guid = "rs_guid"
    recordset_uuid = "rs_uuid"

    '''Test add_batch with minimum correct information.'''
    batch = model.add_batch(
        path, accountID, license, licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, None, None, None, None, None)
    self._validateBatchFields(
        batch, path, accountID, license, licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, "", "", "", "", "")
    
    # Batch information will be used in _testAddImage.
    self._batch1 = batch

    '''Test add_batch with full correct information.'''
    keyword = "kw1, kw2"
    proID = "providerID"
    pubID = "publisherID"
    fundingSource = "fundingsource"
    fundingPurpose = "fundingpurpose"
    batch = model.add_batch(
        path, accountID, license, licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, keyword, proID, pubID, fundingSource,
        fundingPurpose)
    self._validateBatchFields(
        batch, path, accountID, license, licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, keyword, proID, pubID, fundingSource,
        fundingPurpose)

    # Batch information will be used in _testAddImage.
    self._batch2 = batch

    '''Test add_batch with invalid file path.'''
    invalid_path = "invalid/path/file.csv"
    self.assertRaises(model.ModelException, model.add_batch,
        invalid_path, accountID, license, licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, None, None, None, None, None)

    '''Test add_batch with required field "license" empty.'''
    self.assertRaises(model.ModelException, model.add_batch,
        invalid_path, accountID, "", licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, None, None, None, None, None)

  def _testAddImage(self):
    '''Test add_image with various inputs.'''
    # We are going to use the batches, make sure they are valid and different.
    self.assertIsNotNone(self._batch1)
    self.assertIsNotNone(self._batch2)
    self.assertNotEqual(self._batch1, self._batch2)

    headerline = ["idigbio:OriginalFileName", "idigbio:MediaGUID"]
    mediaguid = "123123123" # Random
    rs_uuid = "837168372" # Random
    
    '''A correct file path with minimum input.'''
    orig_filepath = os.path.join(os.getcwd(), "image1.jpg")
    csvrow = [orig_filepath, mediaguid]
    record = model.add_image(self._batch1, csvrow, headerline)
    self._validateImageRecordFields(record, orig_filepath, mediaguid, "", "",
                                    "image/jpeg", 143978, "{}", self._batch1.id)
    '''If the image is a retry, update the batch ID.'''
    model.commit()
    record = model.add_image(self._batch2, csvrow, headerline)
    self._validateImageRecordFields(record, orig_filepath, mediaguid, "", "",
                                    "image/jpeg", 143978, "{}", self._batch2.id)
    '''If the image is uploaded, just return None.'''
    # Update the UploadTime of the record.
    record.UploadTime = str(datetime.datetime.utcnow())
    model.commit()
    self.assertIsNone(model.add_image(self._batch1, csvrow, headerline))
    # Record the imagerecord information for testing other functions.
    self._record = record
    '''A correct large input.'''
    annotation = {"Field1": "Value1", "Field2": "Value2", "Field3": "Value3"}
    headerline2 = ["idigbio:OriginalFileName", "idigbio:MediaGUID", "Field1",
                   "Field2", "Field3"]
    mediaguid2 = "1231231232" # Random
    rs_uuid2 = "9416729378" # Random
    csvrow2 = [orig_filepath, mediaguid2, annotation["Field1"],
               annotation["Field2"], annotation["Field3"]]
    record = model.add_image(self._batch2, csvrow2, headerline2)
    self._validateImageRecordFields(
        record, orig_filepath, mediaguid2, "", "", "image/jpeg", 143978,
        str(annotation), self._batch2.id)

    '''File path is wrong.'''
    invalid_filepath = "Invalid/path/file.jpg"
    csvrow = [invalid_filepath, mediaguid]
    record = model.add_image(self._batch1, csvrow, headerline)
    self._validateImageRecordFields(
        record, invalid_filepath, mediaguid, "File not found.", "",
        "image/jpeg", "", "{}", self._batch1.id)

  def _testGetAllBatches(self):
    '''
    Test get_all_batches. Compare the queried batches with the recorded
    information.
    '''
    # We are going to use _batch1 and _batch2, make sure they are valid.
    self.assertIsNotNone(self._batch1)
    self.assertIsNotNone(self._batch2)

    model.commit()
    batches = model.get_all_batches()
    batch1 = batches[0]
    self._validateBatchFields(
        self._batch1, batch1[1], batch1[2], batch1[3], batch1[4], batch1[5],
        batch1[6], batch1[7], batch1[10], batch1[11], batch1[12], batch1[13],
        batch1[14])
    batch2 = batches[1]
    self._validateBatchFields(
        self._batch2, batch2[1], batch2[2], batch2[3], batch2[4], batch2[5],
        batch2[6], batch2[7], batch2[10], batch2[11], batch2[12], batch2[13],
        batch2[14])

  def _testGetBatchDetails(self):
    '''
    Test get_batch_details. Compare the queried imagerecord with the recorded
    information.
    '''
    # We are going to use _record and _batch2, make sure they are valid.
    self.assertIsNotNone(self._record)
    self.assertIsNotNone(self._batch2)

    model.commit()
    records = model.get_batch_details(self._batch2.id)
    record = records[0]

    self._validateImageRecordFields(
        self._record, record[0], record[1], record[2], record[3], record[8],
        record[9], record[13], record[28])

    self._validateBatchFields(
        self._batch2, record[16], record[17], record[18], record[19],
        record[20], record[21], record[22], record[23], record[24], record[25],
        record[26], record[27])

  def _testGetLastBatchInfo(self):
    '''Test get_last_batch_info.'''
    # We are going to use _batch2, make sure it is valid.
    self.assertIsNotNone(self._batch2)
    self.assertIsNone(self._batch2.finish_time)

    model.commit()
    '''The batch is not finished.'''
    retdict = model.get_last_batch_info()
    self.assertFalse(retdict["Empty"])
    self.assertEqual(retdict["path"], self._batch2.CSVfilePath)
    self.assertIsNotNone(retdict["start_time"])
    self.assertIsNone(retdict["ErrorCode"])
    self.assertFalse(retdict["finished"])

    '''The batch is finished.'''
    self._batch2.finish_time = datetime.datetime.now()
    retdict = model.get_last_batch_info()
    self.assertFalse(retdict["Empty"])
    self.assertEqual(retdict["path"], self._batch2.CSVfilePath)
    self.assertIsNotNone(retdict["start_time"])
    self.assertIsNone(retdict["ErrorCode"])
    self.assertTrue(retdict["finished"])

  def runTest(self):
    self._testAddBatch()
    self._testAddImage()
    self._testGetAllBatches()
    self._testGetBatchDetails()
    self._testGetLastBatchInfo()

class TestIngestionManager(unittest.TestCase):
  def setUp(self):
    api_client.init("http://beta-api.idigbio.org/v1")
    self._testDB = os.path.join(os.getcwd(), "idigbio.ingest.db")
    if os.path.exists(self._testDB):
      os.remove(self._testDB) # Make sure the database is clean.
    model.setup(os.path.join(os.getcwd(), "idigbio.ingest.db"))
    user_config.setup(os.path.join(os.getcwd(), "user.config"))
    api_client.authenticate("60f7cb1e-02f5-425c-bc37-cae87550317a",
                            "99f3ea05d8229a2f0d3aa1fcadf4a9a3")
  def tearDown(self):
    '''Clean up the tmp db file.'''
    model.close()
    os.remove(self._testDB)

  def _testUploadTask(self):
    '''Test 1'''
    values = {
      user_config.CSV_PATH: os.path.join(os.getcwd(), "file1.csv"),
      user_config.RECORDSET_GUID: "testUploadCsv1",
      user_config.RIGHTS_LICENSE: "CC0",
      user_config.MEDIACONTENT_KEYWORD: "kw1",
      user_config.IDIGBIO_PROVIDER_GUID: "proguid",
      user_config.IDIGBIO_PUBLISHER_GUID: "pubguid",
      user_config.FUNDING_SOURCE: "fundingsource",
      user_config.FUNDING_PURPOSE: "fundingpurpose"}
    ingestion_manager.upload_task(values)

    '''Task 2'''
    values[user_config.CSV_PATH] = os.path.join(os.getcwd(), "file2.csv")
    values[user_config.RECORDSET_GUID] = "testUploadCsv2"
    ingestion_manager.upload_task(values)

  def _testGetResult(self):
    '''Test get_result. Should be finished now.'''
    result = ingestion_manager.get_result()
    self.assertIsNotNone(result)

  def runTest(self):
    self._testUploadTask()
    self._testGetResult()

if __name__ == '__main__':
      unittest.main()
