#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This is module manages the queue of tasks to be executed.
"""
import cherrypy, Queue, os
from datetime import datetime, timedelta
from dataingestion.task_queue import BackgroundTaskQueue
from dataingestion.services import (ingestion_manager, constants, api_client,
                                    csv_generator, user_config)
from dataingestion.services.user_config import (get_user_config,
                                                set_user_config, rm_user_config)

singleton_task = BackgroundTaskQueue(cherrypy.engine, qsize=1, qwait=20)
singleton_task.subscribe()
singleton_task.start()

def _upload_task(values):
  api_client.authenticate(get_user_config('accountuuid'),
                          get_user_config('apikey'))
  ingestion_manager.upload_task(values)
  cherrypy.log('Upload task finished.',  __name__)

def start_upload(values=None):
  """
  Start the upload tasks and then return.
  Parameter:
    values: A list of values in the upload. If None, it means this is a resume.
  Returns: True if a task is added to the queue. False if queue is full.
  """
  if values:
    # Initial checks before the task is added to the queue.
    path = values[user_config.CSV_PATH]
    if not os.path.exists(path):
      raise ValueError('CSV file \"' + path + '\" does not exist.')
    elif os.path.isdir(path):
      raise ValueError('The CSV path is a directory.')
  try:
    return singleton_task.put(_upload_task, values)
  except Queue.Full:
    cherrypy.log('Task ongoing.')

