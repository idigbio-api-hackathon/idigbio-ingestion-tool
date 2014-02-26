#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This module implements the core logic that manages the upload process.
"""
import os, logging, argparse, tempfile, atexit, cherrypy, csv, json, tempfile
import hashlib
from functools import partial
from datetime import datetime
from Queue import Empty, Queue
from threading import enumerate as threading_enumerate, Thread
from time import sleep
from sys import exc_info
from os.path import isdir, join
from traceback import format_exception
from errno import ENOENT
from dataingestion.services.api_client import (ClientException, Connection,
                                               ServerException)
from dataingestion.services import model, user_config, constants
import ast

logger = logging.getLogger('iDigBioSvc.ingestion_manager')

ongoing_upload_task = None
fatal_server_error = False 
input_csv_error = False 

class IngestServiceException(Exception):
  def __init__(self, msg, reason=''):
    Exception.__init__(self, msg)
    self.reason = reason

class InputCSVException(Exception): 
  def __init__(self, msg, reason=''):
    Exception.__init__(self, msg)
    self.reason = reason

def _get_conn():
  """
  Get connection.
  """
  return Connection()

def _put_errors_from_threads(threads):
  """
  Places any errors from the threads into error_queue.
  :param threads: A list of QueueFunctionThread instances.
  :returns: True if any errors were found.
  """
  was_error = False
  for thread in threads:
    for info in thread.exc_infos:
      was_error = True
      if isinstance(info[1], ClientException):
        logger.error("ClientException: " + str(info[1]))
      else:
        logger.error("Non-ClientException: " +
                ''.join(format_exception(*info)))
        logger.error("Task failed for unkown reason.")
        raise IngestServiceException("Task failed for unkown reason.")
  return was_error

class QueueFunctionThread(Thread):

  def __init__(self, queue, func, *args, **kwargs):
    """
    Calls func for each item in queue; func is called with a queued
    item as the first arg followed by *args and **kwargs. Use the abort
    attribute to have the thread empty the queue (without processing)
    and exit.
    """
    Thread.__init__(self)
    self.abort = False
    self.queue = queue
    self.func = func
    self.args = args
    self.kwargs = kwargs
    self.exc_infos = []

  def run(self):
    global fatal_server_error
    while True:
      try:
        item = self.queue.get_nowait()
        if not self.abort:
          self.func(item, *self.args, **self.kwargs)
        self.queue.task_done()
      except Empty:
        if self.abort:
          break
        sleep(0.01)
      except ServerException as e: 
        logger.error("Fatal Server Error Detected") 
        logger.debug("Fatal Server Error Detected") 
        fatal_server_error = True
      except Exception as ex:
        logger.error("Exception caught in a QueueFunctionThread.")
        self.exc_infos.append(exc_info())
        logger.debug("Thread exiting...")

  def abort_thread(self):
    self.abort = True

# This makes a ongoing_upload_task.
class BatchUploadTask:
  """
  State about a single batch upload task.
  """
  STATUS_FINISHED = "finished"
  STATUS_RUNNING = "running"

  def __init__(self, batch=None, max_continuous_fails=1000):
    self.batch = batch
    self.total_count = 0
    self.object_queue = Queue()
    self.status = None
    self.error_msg = None
    self.postprocess_queue = Queue()
    self.error_queue = Queue()
    self.success_count = 0
    self.skips = 0
    self.fails = 0
    self.continuous_fails = 0
    self.max_continuous_fails = max_continuous_fails
 
  # Increment a field's value by 1.
  def increment(self, field_name):
    if hasattr(self, field_name) and type(getattr(self, field_name)) == int:
      setattr(self, field_name, getattr(self, field_name) + 1)
    else:
      logger.error("BatchUploadTask object doesn't have this field or " +
               "has has a field that cannot be incremented.")
      raise ValueError("BatchUploadTask object doesn't have this field or " +
               "has has a field that cannot be incremented.")

  # Update the continuous failure times.
  def check_continuous_fails(self, succ_this_time):
    """
    :return: Whether this upload should be aborted.
    """
    if succ_this_time:
      #if self.continuous_fails != 0:
      #  logger.debug('Continuous fails is going to be reset due to a success.')
      self.continuous_fails = 0
      return False
    else:
      self.continuous_fails += 1

    if self.continuous_fails <= self.max_continuous_fails:
      return False
    else:
      return True

def get_progress():
  """
  Return (total items, skips, successes, fails).
  """
  task = ongoing_upload_task
  global fatal_server_error
  global input_csv_error 

  if task is None:
    logger.error("No ongoing upload task.")
    raise IngestServiceException("No ongoing upload task.")

  while (task.total_count == 0 and
      task.status != BatchUploadTask.STATUS_FINISHED):
    # Things are yet to be added.
    sleep(0.1)

  return (fatal_server_error, input_csv_error, task.total_count, task.skips,
          task.success_count, task.fails, ongoing_upload_task.batch.CSVUploaded,
          True if task.status == BatchUploadTask.STATUS_FINISHED else False)

def get_result():
  """
  Return the details of the ongoing task.
  """
  # The result is given only when all the tasks are finished.
  while ongoing_upload_task.status != BatchUploadTask.STATUS_FINISHED:
    sleep(0.1)
  if ongoing_upload_task.batch:
    return model.get_batch_details(ongoing_upload_task.batch.id)
  else:
    # If the task fails before the batch is created (e.g. fail to post a
    # record set), then the batch could be None.
    logger.error("No batch is found.")
    raise IngestServiceException("No batch is found.")

def get_history(batch_id):
  """
  If batch_id is not given, return all batches.
  Otherwise, return the details of the batch with batch_id.
  """
  if batch_id is None or batch_id == "":
    return model.get_all_batches()
  else:
    return model.get_batch_details(batch_id)

def upload_task(values):
  """
  Execute either a new upload task or resume last unsuccessful upload task
  from the DB.
  This method returns true when all file upload tasks are executed and
  postprocess and error queues are emptied.
  Return: False is the upload is not executed due to an existing ongoing task.
  """
  global ongoing_upload_task
  global input_csv_error 

  if (ongoing_upload_task and
      ongoing_upload_task.status != BatchUploadTask.STATUS_FINISHED):
    # Ongoing task exists
    return False

  ongoing_upload_task = BatchUploadTask()
  ongoing_upload_task.status = BatchUploadTask.STATUS_RUNNING

  postprocess_queue = ongoing_upload_task.postprocess_queue

  def _postprocess(func=None, *args):
    func and func(*args)

  # postprocess_thread is a new thread post processing the tasks?
  postprocess_thread = QueueFunctionThread(postprocess_queue, _postprocess)
  postprocess_thread.start()

  def _error(item):
    logger.error(item)

  # error_thread is a new thread logging the errors.
  error_queue = ongoing_upload_task.error_queue
  error_thread = QueueFunctionThread(error_queue, _error)
  error_thread.start()

  try:
    try:
      _upload_images(ongoing_upload_task, values)
    except (ClientException, IOError):
      error_queue.put(str(IOError))
    while not postprocess_queue.empty():
      sleep(0.01)
    postprocess_thread.abort = True
    while postprocess_thread.isAlive():
      postprocess_thread.join(0.01)
    try:
      if (ongoing_upload_task.success_count != 0):
        _upload_csv(ongoing_upload_task.batch, _get_conn())
      if ongoing_upload_task.fails == 0: # All done.
        ongoing_upload_task.batch.finish_time = datetime.now()
        model.commit()
    except (ClientException, IOError):
      error_queue.put(str(IOError))
    while not error_queue.empty():
      sleep(0.01)
    error_thread.abort = True
    while error_thread.isAlive():
      error_thread.join(0.01)

    logger.info("Upload task execution completed.")
  except InputCSVException as e: 
    logger.debug("Input CSV File error ")  
    input_csv_error = True

  except (SystemExit, Exception) as ex:
    logger.error("Error happens in _upload: %s" %ex)
    logger.error("Aborting all threads...")
    for thread in threading_enumerate():
      thread.abort = True
    raise
  finally:
    # Reset of singleton task in the module.
    ongoing_upload_task.status = BatchUploadTask.STATUS_FINISHED

def _upload_images(ongoing_upload_task, values):
  object_queue = ongoing_upload_task.object_queue
  postprocess_queue = ongoing_upload_task.postprocess_queue
  error_queue = ongoing_upload_task.error_queue
  global fatal_server_error 

  conn = _get_conn()
  try:
    if not values: # Resume.
      logger.debug("Resume last batch.")

      oldbatch = model.load_last_batch()
      if oldbatch.finish_time:
        logger.error("Last batch already finished, why resume?")
        raise IngestServiceException("Last batch already finished, why resume?")
      # Assign local variables with values in DB.
      CSVfilePath = oldbatch.CSVfilePath
      #batch.id = batch.id + 1
      batch = model.add_batch(
          oldbatch.CSVfilePath, oldbatch.iDigbioProvidedByGUID,
          oldbatch.RightsLicense, oldbatch.RightsLicenseStatementUrl,
          oldbatch.RightsLicenseLogoUrl)
      model.commit()
    else: # Not resume. It is a new upload.
      logger.debug("Start a new csv batch.")

      CSVfilePath = values[user_config.CSV_PATH]
      iDigbioProvidedByGUID = user_config.get_user_config(
          user_config.IDIGBIOPROVIDEDBYGUID)
      RightsLicense = values[user_config.RIGHTS_LICENSE]
      license_set = constants.IMAGE_LICENSES[RightsLicense]
      RightsLicenseStatementUrl = license_set[2]
      RightsLicenseLogoUrl = license_set[3]

      # Insert into the database.
      logger.debug("Insert batch into the database")
      batch = model.add_batch(
          CSVfilePath, iDigbioProvidedByGUID, RightsLicense,
          RightsLicenseStatementUrl, RightsLicenseLogoUrl) 
      model.commit()

    ongoing_upload_task.batch = batch

    worker_thread_count = 1
    # the object_queue and _image_job are passed to the thread.
    object_threads = [QueueFunctionThread(object_queue, _image_job,
        batch, _get_conn()) for _junk in xrange(worker_thread_count)]
    ongoing_upload_task.object_threads = object_threads

    # Put all the records to the data base and the job queue.
    # Get items from the CSV row, which is an array.
    # In current version, the row is simply [path, providerid].
    logger.debug('Put all image records into db...')
    with open(CSVfilePath, 'rb') as csvfile:
      csv.register_dialect('mydialect', delimiter=',', quotechar='"',
                           skipinitialspace=True)
      reader = csv.reader(csvfile, 'mydialect')
      headerline = None
      recordCount = 0
      for row in reader: # For each line do the work.
        if not headerline:
          batch.ErrorCode = "CSV File Format Error."
          headerline = row
          batch.ErrorCode = ""
          continue

        # Validity test for each line in CSV file  
        if len(row) != len(headerline):
          logger.debug("Input CSV File weird. At least one row has different"
              + " number of columns")
          raise InputCSVException("Input CSV File weird. At least one row has"
              + " different number of columns")

        for col in row: 
          if "\"" in col:  
            logger.debug("One of CSV field contains \"(Double Quatation)")
            raise InputCSVException(
                "One of CSV field contains Double Quatation Mark(\")") 

        # Get the image record
        image_record = model.add_image(batch, row, headerline)
        logger.debug("image_record {0}:".format(image_record))

        fn = partial(ongoing_upload_task.increment, 'total_count')
        postprocess_queue.put(fn)

        if image_record is None:
          # Skip this one because it's already uploaded.
          # Increment skips count and return.
          fn = partial(ongoing_upload_task.increment, 'skips')
          postprocess_queue.put(fn)
        else:
          object_queue.put(image_record)

        logger.debug("image_record on queue")

        recordCount = recordCount + 1
      batch.RecordCount = recordCount
      model.commit()
    logger.debug('Put all image records into db done.')

    for thread in object_threads:
      thread.start()
    logger.debug(
        '{0} upload worker threads started.'.format(worker_thread_count))

    # Wait until all images are executed.
    #while not object_queue.empty():
    #  sleep(0.01)
    while ((ongoing_upload_task.skips + ongoing_upload_task.success_count + 
        ongoing_upload_task.fails) != ongoing_upload_task.total_count):
      if fatal_server_error: 
        raise ServerException  
      sleep(1)
    
    for thread in object_threads:
      thread.abort = True
      while thread.isAlive():
        thread.join(0.01)

    batch.FailCount = ongoing_upload_task.fails
    batch.SkipCount = ongoing_upload_task.skips

    was_error = _put_errors_from_threads(object_threads)
    if not was_error:
      logger.info("Image upload finishes with no error")
    else:
      logger.error("Image upload finishes with errors.")

  except ClientException:
    error_queue.put('Upload failed outside of the worker thread.')
  except IngestServiceException as ex:
    error_queue.put('Upload failed outside of the worker thread.')

  finally:
    model.commit()

# This function is passed to the threads.
def _image_job(image_record, batch, conn):
  global ongoing_upload_task
  try:
    logger.debug("--------------- An image job is started -----------------")
    if not batch:
      raise ClientException("Batch record is None.")
    if not image_record:
      raise ClientException("image_recod is None.")

    logger.debug("OriginalFileName: " + image_record.OriginalFileName)

    if image_record.Error:
      raise ClientException(image_record.Error)

    # First, change the batch ID to this one. This field is overwriten.
    image_record.BatchID = str(batch.id)
    # Post image to API.
    # ma_str is the return from server
    img_str = conn.post_image(
        image_record.OriginalFileName, image_record.MediaGUID)
    image_record.MediaAPContent = img_str
    result_obj = json.loads(img_str)
    url = result_obj["file_url"]

    # img_etag is not stored in the db.
    img_etag = result_obj["file_md5"]

    # Check the image integrity.
    if img_etag and image_record.MediaMD5 == img_etag:
      image_record.UploadTime = str(datetime.utcnow())
      image_record.MediaURL = url
    else:
      logger.error("Upload failed because local MD5 does not match the eTag"
          + " or no eTag is returned.")
      raise ClientException("Upload failed because local MD5 does not match"
          + " the eTag or no eTag is returned.")
    if conn.attempts > 1:
      logger.debug('Done after %d attempts' % (conn.attempts))
    else:
      logger.debug('Done after %d attempts' % (conn.attempts))

    # Increment the success_count by 1.
    fn = partial(ongoing_upload_task.increment, 'success_count')
    ongoing_upload_task.postprocess_queue.put(fn)
    # It's sccessful this time.
    fn = partial(ongoing_upload_task.check_continuous_fails, True)
    ongoing_upload_task.postprocess_queue.put(fn)
  except ClientException as ex:
    logger.error("ClientException: An image job failed. Reason: %s" %ex)
    fn = partial(ongoing_upload_task.increment, 'fails')
    ongoing_upload_task.postprocess_queue.put(fn)
    def _abort_if_necessary():
      if ongoing_upload_task.check_continuous_fails(False):
        logger.info("Aborting threads because continuous failures exceed the"
            + " threshold.")
        map(lambda x: x.abort_thread(), ongoing_upload_task.object_threads)
    ongoing_upload_task.postprocess_queue.put(_abort_if_necessary)
    raise
  except IOError as err:
    logger.error("IOError: A CSV job failed.")
    if err.errno == ENOENT: # No such file or directory.
      error_queue.put(
          'Local file %s not found' % repr(image_record.OriginalFileName))
      fn = partial(ongoing_upload_task.increment, 'fails')
      ongoing_upload_task.postprocess_queue.put(fn)
    else:
      raise

def _upload_csv(batch, conn):
  try:
    logger.debug("--------------- An CSV job is started -----------------")
    if not batch:
      raise ClientException("Batch record is None.")

    # Post csv file to API.
    # ma_str is the return from server
    name, f_md5 = _make_csvtempfile(batch)
    csv_str = conn.post_csv(name)
    result_obj = json.loads(csv_str)

    # img_etag is not stored in the db.
    csv_etag = result_obj['file_md5']

    # Check the image integrity.
    if csv_etag != f_md5:
      logger.error("Upload failed because local MD5 does not match the eTag"
          + " or no eTag is returned.")
      raise ClientException("Upload failed because local MD5 does not match"
          + " the eTag or no eTag is returned.")
    logger.debug('Done after %d attempts' % (conn.attempts))
    batch.CSVUploaded = True
  except ClientException as ex:
    logger.error("ClientException: A CSV job failed. Reason: %s" %ex)
    raise
  except IOError as err:
    logger.error("IOError: A CSV job failed.")
    raise

def _make_csvtempfile(batch):
  logger.debug("Making temporary CSV file ...")
  fname = os.path.join(tempfile.gettempdir(), "temp.csv")
  md5 = ""
  with open(fname, "wb") as f:
    header = model.get_batch_details_fieldnames()
    f.write(",".join(header) + "\n")
    rows = model.get_batch_details(batch.id)
    for row in rows:
      for item in row:
        if item is None:
          f.write(",")
        else:
          f.write(str(item) + ",")
      f.write("\n")
  with open(fname, "rb") as f:
    md5 = _md5_file(f)
  logger.debug("Making temporary CSV file done.")
  return fname, md5

def _md5_file(f, block_size=2*20):
  md5 = hashlib.md5()
  while True:
    data = f.read(block_size)
    if not data:
      break
    md5.update(data)
  return md5.hexdigest()
