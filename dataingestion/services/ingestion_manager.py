#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This module implements the core logic that manages the upload process.
"""
import os, logging, argparse, tempfile, atexit, cherrypy, re, csv
import json
from functools import partial
from datetime import datetime
from Queue import Empty, Queue
from threading import enumerate as threading_enumerate, Thread
from time import sleep
from sys import exc_info
from os.path import isdir, join
from traceback import format_exception
from errno import ENOENT
from dataingestion.services.api_client import ClientException, Connection
from dataingestion.services import model, user_config, constants

logger = logging.getLogger('iDigBioSvc.ingestion_manager')

ongoing_upload_task = None
""" Singleton upload task. """

class IngestServiceException(Exception):
    def __init__(self, msg, reason=''):
        Exception.__init__(self, msg)
        self.reason = reason

def get_conn():
    """
    Get connection.
    """
    return Connection()

def put_errors_from_threads(threads):
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
                raise IngestServiceException("Task failed for unkown reason.")
    return was_error

class QueueFunctionThread(Thread):

    def __init__(self, queue, func, *args, **kwargs):
        """ Calls func for each item in queue; func is called with a queued
        item as the first arg followed by *args and **kwargs. Use the abort
        attribute to have the thread empty the queue (without processing)
        and exit. """
        Thread.__init__(self)
        self.abort = False
        self.queue = queue
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.exc_infos = []

    def run(self):
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
            except Exception:
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

    def __init__(self, tasktype=constants.CSV_TYPE, batch=None, max_continuous_fails=1000):
        self.tasktype = tasktype
        self.batch = batch
        self.total_count = 0
        self.object_queue = Queue(10000)
        self.status = None
        self.error_msg = None
        self.postprocess_queue = Queue(10000)
        self.error_queue = Queue(10000)
        self.skips = 0
        self.fails = 0
        self.success_count = 0
        self.continuous_fails = 0
        self.max_continuous_fails = max_continuous_fails
        
    # Increment a field's value by 1.
    def increment(self, field_name):
        if hasattr(self, field_name) and type(getattr(self, field_name)) == int:
            setattr(self, field_name, getattr(self, field_name) + 1)
        else:
            raise ValueError("BatchUploadTask object doesn't have this field or " +
                             "has has a field that cannot be incremented.")
    
    # Update the continuous failure times.
    def check_continuous_fails(self, succ_this_time):
        '''
        :return: Whether this upload should be aborted.
        '''
        if succ_this_time:
            if self.continuous_fails != 0:
                logger.debug('Continuous fails is going to be reset due to a success.')
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

    if task is None:
        raise IngestServiceException("No ongoing upload task.")
    
    while task.total_count == 0 and task.status != BatchUploadTask.STATUS_FINISHED:
        # Things are yet to be added.
        sleep(0.1)

    return (task.total_count, task.skips, task.success_count, task.fails,
        True if task.status == BatchUploadTask.STATUS_FINISHED else False)

def get_result():
    # The result is given only when all the tasks are finished.
    while ongoing_upload_task.status != BatchUploadTask.STATUS_FINISHED:
        sleep(0.1)
    
    if ongoing_upload_task.batch:
        return model.get_batch_details(ongoing_upload_task.batch.id)
    else:
        # If the task fails before the batch is created (e.g. fail to post a
        # record set), then the batch could be None.
        raise IngestServiceException("No batch is found.")

def exec_upload_task(root_path=None, resume=False):
    """
    Execute either a new upload task or resume last unsuccessfuly upload task
    from the DB.
    This method returns true when all file upload tasks are executed and
    postprocess and error queues are emptied.
    :return: False is the upload is not executed due to an existing ongoing task.
    """
    global ongoing_upload_task

    if ongoing_upload_task and ongoing_upload_task.status != BatchUploadTask.STATUS_FINISHED:
        # Ongoing task exists
        return False

    ongoing_upload_task = BatchUploadTask(constants.DIR_TYPE)
    ongoing_upload_task.status = BatchUploadTask.STATUS_RUNNING

    postprocess_queue = ongoing_upload_task.postprocess_queue

    def _postprocess(func=None, *args):
        func and func(*args)

    postprocess_thread = QueueFunctionThread(postprocess_queue, _postprocess)
    postprocess_thread.start()

    def _error(item):
        logger.error(item)

    error_queue = ongoing_upload_task.error_queue
    error_thread = QueueFunctionThread(error_queue, _error)
    error_thread.start()

    try:
        try:
            _upload(ongoing_upload_task, root_path, resume)
        except (ClientException, IOError):
            error_queue.put(str(IOError))
        while not postprocess_queue.empty():
            sleep(0.01)
        postprocess_thread.abort = True
        while postprocess_thread.isAlive():
            postprocess_thread.join(0.01)
        while not error_queue.empty():
            sleep(0.01)
        error_thread.abort = True
        while error_thread.isAlive():
            error_thread.join(0.01)

        logger.info("Upload task execution completed.")

    except (SystemExit, Exception):
        logger.error("Aborting all threads...")
        for thread in threading_enumerate():
            thread.abort = True
        raise
    finally:
        # Reset of singleton task in the module.
        ongoing_upload_task.status = BatchUploadTask.STATUS_FINISHED

def exec_upload_csv_task(csv_path=None, resume=False):
    """
    Execute either a new upload task or resume last unsuccessfuly upload task
    from the DB.
    This method returns true when all file upload tasks are executed and
    postprocess and error queues are emptied.
    :return: False is the upload is not executed due to an existing ongoing task.
    """
    global ongoing_upload_task

    if ongoing_upload_task and ongoing_upload_task.status != BatchUploadTask.STATUS_FINISHED:
        # Ongoing task exists
        return False

    ongoing_upload_task = BatchUploadTask(constants.CSV_TYPE)
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
            _upload_csv(ongoing_upload_task, resume, csv_path)
        except (ClientException, IOError):
            error_queue.put(str(IOError))
        while not postprocess_queue.empty():
            sleep(0.01)
        postprocess_thread.abort = True
        while postprocess_thread.isAlive():
            postprocess_thread.join(0.01)
        while not error_queue.empty():
            sleep(0.01)
        error_thread.abort = True
        while error_thread.isAlive():
            error_thread.join(0.01)

        logger.info("Upload task execution completed.")

    except (SystemExit, Exception):
        logger.error("Aborting all threads...")
        for thread in threading_enumerate():
            thread.abort = True
        raise
    finally:
        # Reset of singleton task in the module.
        ongoing_upload_task.status = BatchUploadTask.STATUS_FINISHED

def _make_idigbio_metadata(path):
    metadata = {}

    license_key = user_config.get_user_config(user_config.IMAGE_LICENSE)

    license_ = constants.IMAGE_LICENSES[license_key]
    metadata["xmpRights:usageTerms"] = license_[0]
    metadata["xmpRights:webStatement"] = license_[2]
    metadata["ac:licenseLogoURL"] = license_[3]
    # The suffix has already been checked so that extension must be in the
    # dictionary.
    extension = os.path.splitext(path)[1].lstrip('.').lower()
    metadata["idigbio:mediaType"] = constants.EXTENSION_MEDIA_TYPES[extension]
    return metadata

# Upload all the image files within a path.
def _upload(ongoing_upload_task, root_path=None, resume=False):
    pass

def _upload_csv(ongoing_upload_task, resume=False, csv_path=None):
    object_queue = ongoing_upload_task.object_queue
    postprocess_queue = ongoing_upload_task.postprocess_queue
    error_queue = ongoing_upload_task.error_queue

    # This function is passed to the threads.
    def _csv_job(image_record, conn):
        try:
            logger.debug("Started!!!++++++++++++++++++++++++++++++++++")
            logger.debug(object_queue.qsize())
            if image_record is None:
                raise ClientException("image_recod is None.")
            if image_record.file_exist is False:
                raise ClientException("File is not found.")
            if image_record.mr_uuid is None:
                # Post mediarecord.
                logger.debug("image_record.mr_uuid is None.")
                logger.debug("Task 111: post media record.")
                image_record.batch_id = batch.id
                owner_uuid = user_config.try_get_user_config('owneruuid')
                logger.debug("Got owner_uuid.")

                mediapath = image_record.path
                mediaproviderid = image_record.providerid
                logger.debug("Set mediapath and mediaproviderid.")
                
                metadata = _make_idigbio_metadata(mediapath)
                logger.debug("post media record.")

                record_uuid, etag, mr_str = conn.post_mediarecord( # mr_str is the return from server
                    recordset_uuid, mediapath, mediaproviderid, metadata, owner_uuid)
                logger.debug("Got record uuid.")
                image_record.mr_uuid = record_uuid
                image_record.mr_record = mr_str
                image_record.etag = etag
                logger.debug("Task 111 done.")
                model.commit()

            logger.debug("Task 112: post media.")
            # First, change the batch ID to this one. This field is overwriten.
            image_record.batch_id = batch.id
            # Post image to API.
            ma_str = conn.post_media(mediapath, image_record.mr_uuid) # ma_str is the return from server
            image_record.ma_record = ma_str
            result_obj = json.loads(ma_str)
            logger.debug("Task 112 done.")

            url = result_obj["idigbio:links"]["media"][0]
            ma_uuid = result_obj['idigbio:uuid']

            image_record.ma_uuid = ma_uuid

            img_etag = result_obj['idigbio:data'].get('idigbio:imageEtag')

            if img_etag and image_record.media_md5 == img_etag:
                image_record.upload_time = str(datetime.utcnow())
                image_record.url = url
            else:
                raise ClientException('Upload failed because local MD5 does not match the eTag or no eTag is returned.')

            if conn.attempts > 1:
                logger.debug('%s [after %d attempts]' % (mediapath, conn.attempts))
            else:
                logger.debug('%s [after %d attempts]' % (mediapath, conn.attempts))
            
            # Increment the success_count by 1.
            fn = partial(ongoing_upload_task.increment, 'success_count')
            postprocess_queue.put(fn)
            
            # It's sccessful this time.
            fn = partial(ongoing_upload_task.check_continuous_fails, True)
            postprocess_queue.put(fn)
            
        except ClientException:
            logger.error("An CSV job failed.")
            fn = partial(ongoing_upload_task.increment, 'fails')
            ongoing_upload_task.postprocess_queue.put(fn)

            def _abort_if_necessary():
                if ongoing_upload_task.check_continuous_fails(False):
                    logger.info("Aborting threads because continuous failures exceed the threshold.")
                    map(lambda x: x.abort_thread(), ongoing_upload_task.object_threads)
            ongoing_upload_task.postprocess_queue.put(_abort_if_necessary)
            raise
        except IOError as err:
            if err.errno == ENOENT: # No such file or directory.
                error_queue.put('Local file %s not found' % repr(mediapath))
                fn = partial(ongoing_upload_task.increment, 'fails')
                ongoing_upload_task.postprocess_queue.put(fn)
            else:
                raise

    conn = get_conn()
    try:
        if resume:
            logger.debug("Resume batch.")
            batch = model.load_last_batch()
            if batch.finish_time:
                raise IngestServiceException("Last batch already finished, why resume?")
            # Assign local variables with values in DB.
            csv_path = batch.CSVfilePath
            recordset_uuid = batch.RecordSetUUID
            batch.id = batch.id + 1
            model.commit()
        elif csv_path: # Not resume, and csv_path is provided. It is a new upload.
            logger.debug("Start a new csv batch.")
            recordset_guid = user_config.get_user_config(user_config.RECORDSET_ID) # Temporary provider ID
            # TODO: Receive provider id from UI.
            logger.debug('ingestion_manager._upload_csv:post_recordset')
            recordset_uuid = conn.post_recordset(recordset_guid)
            logger.debug('ingestion_manager._upload_csv:got uuid, put into db.')
            iDigbioProvidedByGUID = user_config.get_user_config(user_config.IDIGBIOPROVIDEDBYGUID)
            RightsLicense = user_config.get_user_config(user_config.IMAGE_LICENSE)
            license_ = constants.IMAGE_LICENSES[RightsLicense]
            RightsLicenseStatementUrl = license_[2]
            RightsLicenseLogoUrl = license_[3]
            keyword = user_config.get_user_config(user_config.MEDIACONTENT_KEYWORD)
            providerID = user_config.get_user_config(user_config.IDIGBIO_PROVIDER_GUID)
            publisherID = user_config.get_user_config(user_config.IDIGBIO_PUBLISHER_GUID)
            fundingSource = user_config.get_user_config(user_config.FUNDING_SOURCE)
            fundingPurpose = user_config.get_user_config(user_config.FUNDING_PURPOSE)
            batch = model.add_upload_batch(csv_path, iDigbioProvidedByGUID, RightsLicense, 
                RightsLicenseStatementUrl, RightsLicenseLogoUrl, recordset_guid, 
                recordset_uuid, constants.CSV_TYPE, keyword, providerID, publisherID, fundingSource, 
                fundingPurpose)
            model.commit()
            logger.debug('ingestion_manager._upload_csv:got uuid, committed into db.')
        else:
            raise IngestServiceException("CSV path is not specified.")
        
        ongoing_upload_task.batch = batch

        worker_thread_count = 1
        # the object_queue and _csv_job are passed to the thread.
        object_threads = [QueueFunctionThread(object_queue, _csv_job,
            get_conn()) for _junk in xrange(worker_thread_count)]
        ongoing_upload_task.object_threads = object_threads
        
        for thread in object_threads:
            thread.start()
        logger.debug('{0} upload worker threads started.'.format(worker_thread_count))

        # Put all the records to the data base and the job queue.
        # Get items from the CSV row, which is an array.
        # In current version, the row is simply [path, providerid].
        logger.debug('Task 110: ingestion_manager._upload_csv: put all records from CSV file into db.')
        # Read from the CSV file.
        allowed_files = re.compile(constants.ALLOWED_FILES, re.IGNORECASE)
        with open(csv_path, 'rb') as csvfile:
            logger.debug('aaa')
            csv.register_dialect('mydialect', delimiter=',', quotechar='"', skipinitialspace=True)
            logger.debug('bbb')
            reader = csv.reader(csvfile, 'mydialect')
            logger.debug('ccc')
            for row in reader: # For each line do the work.
                if len(row) != 11:
                    logger.debug(len(row))
                    logger.debug('length of row is not 11.')
                    return
                    # TODO

                logger.debug('Task 110-1')

                mediapath = row[0]
                mediaproviderid = row[1]
                mediapath = mediapath.strip(' ')
                mediaproviderid = mediaproviderid.strip(' ')
                
                logger.debug('Task 110-2')

                if not allowed_files.match(mediapath):
                    continue
                fn = partial(ongoing_upload_task.increment, 'total_count')
                postprocess_queue.put(fn)

                logger.debug("Put in file mediapath="+mediapath+", mediaproviderid="+mediaproviderid)
                # Get the image record
                image_record = model.add_or_load_image(batch, row, recordset_uuid, constants.CSV_TYPE)

                logger.debug('Task 110-3')

                if image_record is None:
                    # Skip this one because it's already uploaded. Increment skips count and return.
                    logger.debug('Skipped file {0}.'.format(mediapath))
                    fn = partial(ongoing_upload_task.increment, 'skips')
                    postprocess_queue.put(fn)
                #elif image_record.file_exist == False:
                    # File not found.
                #    logger.debug('File {0} not found.'.format(mediapath))
                #    fn = partial(ongoing_upload_task.increment, 'fails')
                #    postprocess_queue.put(fn)
                else:
                    logger.debug("Put in job (file may not exist).")
                    object_queue.put(image_record)
        logger.debug('Task 110 done.')


        # Wait until all images are executed.
        #while not object_queue.empty():
        #    sleep(0.01)
        while ((ongoing_upload_task.skips + ongoing_upload_task.success_count + 
            ongoing_upload_task.fails) != ongoing_upload_task.total_count):
            sleep(1)
        
        logger.debug("All finished")
        for thread in object_threads:
            thread.abort = True
            while thread.isAlive():
                thread.join(0.01)

        was_error = put_errors_from_threads(object_threads)
        if not was_error:
            logger.info("Upload finishes with no error")
            batch.finish_time = datetime.now()
        else:
            logger.error("Upload finishes with errors.")

    except ClientException:
        error_queue.put('Upload failed outside of the worker thread.')
        
    finally:
        model.commit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root_path")
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("--db")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.db:
        db_file = args.db
    else:
        db_file = join(tempfile.gettempdir(), "idigbio.ingest.db")
        logger.debug("DB file: {0}".format(db_file))
    model.setup(db_file)
    atexit.register(model.commit)
    exec_upload_task(args.root_path)

if __name__ == '__main__':
    main()
