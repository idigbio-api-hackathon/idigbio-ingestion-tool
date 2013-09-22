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

from dataingestion.services import (api_client, model, user_config,
                                    ingestion_manager)


class TestIngestionManager(unittest.TestCase):
  def setUp(self):
    api_client.init("http://beta-api.idigbio.org/v1")
    self._testDB = os.path.join(os.getcwd(), "idigbio.ingest.db")
    if os.path.exists(self._testDB):
      os.remove(self._testDB) # Make sure the database is clean.
    model.setup(os.path.join(os.getcwd(), "idigbio.ingest.db"))
    user_config.setup(os.path.join(os.getcwd(), "user.config"))
    self.assertTrue(
        api_client.authenticate("60f7cb1e-02f5-425c-bc37-cae87550317a",
                                "99f3ea05d8229a2f0d3aa1fcadf4a9a3"))
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
