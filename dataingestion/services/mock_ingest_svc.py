#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php 
"""
The mock upload service module for testing the UI work.
"""
import time, logging

logger = logging.getLogger('iDigBioSvc.mock_ingest_svc')

remaining = 100
def sleep_task():
    logger.debug("Start to sleep.")
    global remaining
    while (remaining > 0):
        time.sleep(1)
        remaining = remaining - 5
        
def start_upload(root_path):
    sleep_task()
        
def check_progress():
    return 100, remaining