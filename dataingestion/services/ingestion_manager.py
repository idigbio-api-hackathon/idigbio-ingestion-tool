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
import hashlib, threading
from functools import partial
from datetime import datetime
from Queue import Empty, Queue
from threading import enumerate as threading_enumerate, Thread
from time import sleep
from sys import exc_info
from os.path import join
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
        fatal_server_error = True
      except Exception as ex:
        logger.error("Exception caught in a QueueFunctionThread:".format(ex))
        self.exc_infos.append(exc_info())
        logger.debug("Thread exiting...")

  def abort_thread(self):
    self.abort = True

batch_attr_lock = threading.Lock()
batch_check_lock = threading.Lock()
class BatchUploadTask:
  """
  State about a single batch upload task.
  Note: batchUploadTask is threadsafe.
  functions are used to do exclusive access to attributes.
  """
  STATUS_FINISHED = "finished"
  STATUS_RUNNING = "running"

  def __init__(self, batch=None, max_continuous_fails=1000):
    self.batch = batch
    self.object_queue = Queue() # Thread safe object in python.
    self.postprocess_queue = Queue() # Thread safe object in python.
    self.error_queue = Queue() # Thread safe object in python.

    self._total_count = 0
    self._status = None
    self._error_msg = None
    self._successes = 0
    self._skips = 0
    self._fails = 0
    self._continuous_fails = 0
    self._max_continuous_fails = max_continuous_fails
    self._csv_uploaded = False

  def not_started(self):
    batch_attr_lock.acquire()
    not_started = (self._total_count == 0 and self._status != self.STATUS_FINISHED)
    batch_attr_lock.release()
    return not_started

  def get_all_information(self):
    batch_attr_lock.acquire()
    total = self._total_count
    skips = self._skips
    successes = self._successes
    fails = self._fails
    csv = self._csv_uploaded
    status = self._status
    batch_attr_lock.release()

    return total, skips, successes, fails, csv, status

  def is_finished(self):
    batch_attr_lock.acquire()
    finished = (self._skips + self._successes + self._fails == self._total_count)
    batch_attr_lock.release()
    return finished

  def set_csv_uploaded(self):
    batch_attr_lock.acquire()
    self._csv_uploaded = True
    batch_attr_lock.release()

  def csv_uploaded(self):
    batch_attr_lock.acquire()
    ret = self._csv_uploaded
    batch_attr_lock.release()
    return ret

  def get_skips(self):
    batch_attr_lock.acquire()
    count = self._skips
    batch_attr_lock.release()
    return count

  def get_fails(self):
    batch_attr_lock.acquire()
    count = self._fails
    batch_attr_lock.release()
    return count

  def get_successes(self):
    batch_attr_lock.acquire()
    count = self._successes
    batch_attr_lock.release()
    return count

  def get_total_count(self):
    batch_attr_lock.acquire()
    count = self._total_count
    batch_attr_lock.release()
    return count

  def get_status(self):
    batch_attr_lock.acquire()
    status = self._status
    batch_attr_lock.release()
    return status

  def set_status(self, status):
    batch_attr_lock.acquire()
    self._status = status
    batch_attr_lock.release()

  # Increment a field's value by 1.
  def increment(self, field_name_orig):
    batch_attr_lock.acquire()
    field_name = "_" + field_name_orig
    try:
      if hasattr(self, field_name) and type(getattr(self, field_name)) == int:
        setattr(self, field_name, getattr(self, field_name) + 1)
      else:
        logger.error("BatchUploadTask object doesn't have this field or " +
            "has a field that cannot be incremented: {0}".format(field_name))
        raise ValueError("BatchUploadTask object doesn't have this field or " +
            "has a field that cannot be incremented: {0}".format(field_name))
    finally:
      batch_attr_lock.release()

  # Update the continuous failure times.
  def check_continuous_fails(self, succ_this_time):
    """
    :return: Whether this upload should be aborted.
    """
    batch_check_lock.acquire()
    try:
      if succ_this_time:
        self._continuous_fails = 0
        return False
      else:
        self._continuous_fails += 1

      if self._continuous_fails <= self._max_continuous_fails:
        return False
      else:
        return True
    finally:
      batch_check_lock.release()

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

  while(task.not_started()):
    sleep(0.2)

  total, skips, successes, fails, csv, status = task.get_all_information()
  return (fatal_server_error, input_csv_error, total, skips, successes, fails,
          csv,
          True if status == BatchUploadTask.STATUS_FINISHED else False)

def get_result():
  """
  Return the details of the ongoing task.
  """
  # The result is given only when all the tasks are finished.
  while ongoing_upload_task.get_status() != BatchUploadTask.STATUS_FINISHED:
    sleep(0.2)
  if ongoing_upload_task.batch:
    return model.get_batch_details_brief(ongoing_upload_task.batch.id)
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
    return model.get_batch_details_brief(batch_id)

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
      ongoing_upload_task.get_status() != BatchUploadTask.STATUS_FINISHED):
    # Ongoing task exists
    return False

  try:
    ongoing_upload_task = BatchUploadTask()
    ongoing_upload_task.set_status(BatchUploadTask.STATUS_RUNNING)

    postprocess_queue = ongoing_upload_task.postprocess_queue

    def _postprocess(func=None, *args):
      func and func(*args)

    postprocess_thread = QueueFunctionThread(postprocess_queue, _postprocess)
    postprocess_thread.start()

    def _error(item):
      logger.error(item)

    # error_thread is a new thread logging the errors.
    error_queue = ongoing_upload_task.error_queue
    error_thread = QueueFunctionThread(error_queue, _error)
    error_thread.start()

    # Multi-threaded from here.
    try:
      _upload_images(ongoing_upload_task, values)
    except (ClientException, IOError):
      error_queue.put(str(IOError))
    while not postprocess_queue.empty():
      sleep(0.2)
    postprocess_thread.abort = True
    while postprocess_thread.isAlive():
      postprocess_thread.join(0.01)
    try:
      _upload_csv(_get_conn())
      if (ongoing_upload_task.get_fails() == 0
          and ongoing_upload_task.csv_uploaded()): # All done.
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
    ongoing_upload_task.set_status(BatchUploadTask.STATUS_FINISHED)

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
      batch = model.add_batch(
          oldbatch.CSVfilePath, oldbatch.iDigbioProvidedByGUID,
          oldbatch.RightsLicense, oldbatch.RightsLicenseStatementUrl,
          oldbatch.RightsLicenseLogoUrl)
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
    batch_id = str(batch.id)

    worker_thread_count = 10
    # the object_queue and _upload_single_image are passed to the thread.
    object_threads = [QueueFunctionThread(object_queue, _upload_single_image,
        batch_id, _get_conn()) for _junk in xrange(worker_thread_count)]
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
            print col
            logger.debug("One of CSV field contains \"(Double Quatation)")
            raise InputCSVException(
                "One of CSV field contains Double Quatation Mark(\")") 

        # Get the image record
        image_record = model.add_image(batch, row, headerline)

        fn = partial(ongoing_upload_task.increment, 'total_count')
        ongoing_upload_task.postprocess_queue.put(fn)

        if image_record is None:
          # Skip this one because it's already uploaded.
          # Increment skips count and return.
          fn = partial(ongoing_upload_task.increment, 'skips')
          ongoing_upload_task.postprocess_queue.put(fn)
        else:
          object_queue.put(image_record)

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
    while (not ongoing_upload_task.is_finished()):
      if fatal_server_error: 
        raise ServerException  
      sleep(1)
    
    for thread in object_threads:
      thread.abort = True
      while thread.isAlive():
        thread.join(0.01)

    batch.FailCount = ongoing_upload_task.get_fails()
    batch.SkipCount = ongoing_upload_task.get_skips()

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

commit_lock = threading.Lock()

def _upload_single_image(image_record, batch_id, conn):
  '''
  This function is passed to the threads.
  Note: session in model is singleton. It is not thread-safe.
  commit_lock makes sure any access to image_record to be exclusive.
  '''
  global ongoing_upload_task

  filename = ""
  mediaGUID = ""

  commit_lock.acquire()
  try:
    if not image_record:
      logger.error("image_record is None.")
      raise ClientException("image_record is None.")

    logger.info("Image job started: OriginalFileName: {0}"
        .format(image_record.OriginalFileName))

    if image_record.Error:
      logger.error("image record has error: {0}".format(image_record.Error))
      raise ClientException(image_record.Error)
    filename = image_record.OriginalFileName
    mediaGUID = image_record.MediaGUID
  finally:
    commit_lock.release()

  try:
    # Post image to API.
    # ma_str is the return from server
    img_str = conn.post_image(filename, mediaGUID)
    #    image_record.OriginalFileName, image_record.MediaGUID)
    result_obj = json.loads(img_str)
    url = result_obj["file_url"]

    # img_etag is not stored in the db.
    img_etag = result_obj["file_md5"]

    commit_lock.acquire()
    try:
      # First, change the batch ID to this one. This field is overwriten.
      image_record.BatchID = batch_id
      image_record.MediaAPContent = img_str
      # Check the image integrity.
      if img_etag and image_record.MediaMD5 == img_etag:
        image_record.UploadTime = str(datetime.utcnow())
        image_record.MediaURL = url
      else:
        logger.error("Upload failed because local MD5 does not match the eTag"
            + " or no eTag is returned.")
        raise ClientException("Upload failed because local MD5 does not match"
            + " the eTag or no eTag is returned.")
      model.commit()
    finally:
      commit_lock.release()

    if conn.attempts > 1:
      logger.debug('Done after %d attempts' % (conn.attempts))

    # Increment the successes by 1.
    fn = partial(ongoing_upload_task.increment, 'successes')
    ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
    # It's sccessful this time.
    #fn = partial(ongoing_upload_task.check_continuous_fails, True)
    #ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
  except ClientException as ex:
    logger.error("ClientException: An image job failed. Reason: %s" %ex)
    fn = partial(ongoing_upload_task.increment, 'fails')
    ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
    #def _abort_if_necessary():
    #  if ongoing_upload_task.check_continuous_fails(False):
    #    logger.info("Aborting threads because continuous failures exceed the"
    #        + " threshold.")
    #    map(lambda x: x.abort_thread(), ongoing_upload_task.object_threads)
    #ongoing_upload_task.postprocess_queue.put(_abort_if_necessary) # Multi-thread
    raise
  except IOError as err:
    logger.error("IOError: An image job failed.")
    if err.errno == ENOENT: # No such file or directory.
      error_queue.put(
          'Local file %s not found' % repr(image_record.OriginalFileName))
      fn = partial(ongoing_upload_task.increment, 'fails')
      ongoing_upload_task.postprocess_queue.put(fn) # Multi-thread
    else:
      raise

def _upload_csv(conn):
  '''
  We upload all the unuploaded records together.
  '''
  try:
    logger.debug("CSV job started.")

    # Post csv file to API.
    # ma_str is the return from server
    name, f_md5 = _make_csvtempfile()
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
    ongoing_upload_task.set_csv_uploaded()
    model.set_all_csv_uploaded()
  except ClientException as ex:
    logger.error("ClientException: A CSV job failed. Reason: %s" %ex)
    raise
  except IOError as err:
    logger.error("IOError: A CSV job failed.")
    raise

def _make_csvtempfile():
  logger.debug("Making temporary CSV file ...")
  fname = os.path.join(tempfile.gettempdir(), "temp.csv")
  md5 = ""
  with open(fname, "wb") as f:
    csvwriter = csv.writer(
        f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    header = model.get_batch_details_fieldnames()
    csvwriter.writerow(header)
    rows = model.get_unuploaded_information()
    for row in rows:
      csvwriter.writerow(row)
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
