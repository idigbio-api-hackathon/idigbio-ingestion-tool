#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This module implements the core logic that manages the upload process.
"""
import os, logging, argparse, tempfile, atexit
from functools import partial
from datetime import datetime
from Queue import Empty, Queue
from threading import enumerate as threading_enumerate, Thread
from time import sleep
from sys import exc_info
from os.path import isdir, join
import re
from traceback import format_exception
from errno import ENOENT
from dataingestion.services.api_client import ClientException, Connection
from dataingestion.services import model
from dataingestion.services import user_config
from dataingestion.services import constants

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
                logger.error("Unkown exception caught in a QueueFunctionThread.")
                self.exc_infos.append(exc_info())
                logger.debug("Thread exiting...")

    def abort_thread(self):
        self.abort = True
    
class BatchUploadTask:
    """
    State about a single batch upload task.
    """
    STATUS_FINISHED = "finished"
    STATUS_RUNNING = "running"

    def __init__(self, batch=None, max_continuous_fails=2):
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
        
    def increment(self, field_name):
        if hasattr(self, field_name) and type(getattr(self, field_name)) == int:
            setattr(self, field_name, getattr(self, field_name) + 1)
        else:
            raise ValueError("BatchUploadTask object doesn't have this field or " + 
                             "has has a field that cannot be incremented.")
    
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

    ongoing_upload_task = BatchUploadTask()
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
        except ClientException, err:
            error_queue.put(str(err))
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


def make_idigbio_metadata(path):
    metadata = {}

    license_key = user_config.get_user_config('imagelicense')

    license_ = constants.IMAGE_LICENSES[license_key]
    metadata["xmpRights:usageTerms"] = license_[0]
    metadata["xmpRights:webStatement"] = license_[2]
    metadata["ac:licenseLogoURL"] = license_[3]
    # The suffix has already been checked so that extension must be in the 
    # dictionary.
    extension = os.path.splitext(path)[1].lstrip('.')
    metadata["idigbio:mediaType"] = constants.EXTENSION_MEDIA_TYPES[extension]
    return metadata

def _upload(ongoing_upload_task, root_path=None, resume=False):
    """
    This method returns when all file upload tasks have been executed.
    """
    
    object_queue = ongoing_upload_task.object_queue
    postprocess_queue = ongoing_upload_task.postprocess_queue 
    error_queue = ongoing_upload_task.error_queue

    def _object_job(job, conn):
        '''
        The job that uploads a single object (file). 
        '''
        path = job['path']

        try:
            # Get the image record
            image_record = model.add_or_load_image(batch, path)
            if image_record is None:
                # Skip this one because it's already uploaded.
                logger.debug('Skipped file {0}.'.format(path))
                fn = partial(ongoing_upload_task.increment, 'skips')
                postprocess_queue.put(fn)
                return

            # Post mediarecord if necesssary.
            if image_record.mr_uuid is None:
                idsyntax = user_config.get_user_config('idsyntax')
                idprefix = user_config.get_user_config('idprefix')
                idsuffix = path if idsyntax == 'full-path' else os.path.split(path)[1]
                provider_id = idprefix + '/' + idsuffix
                owner_uuid = user_config.try_get_user_config('owneruuid')

                metadata = make_idigbio_metadata(path)
                record_uuid = conn.post_mediarecord(recordset_uuid, path, provider_id, metadata, owner_uuid)
                image_record.mr_uuid = record_uuid

            # Post image to API.
            result_obj = conn.post_media(path, image_record.mr_uuid)
            url = result_obj["idigbio:links"]["media"][0]
            ma_uuid = result_obj['idigbio:uuid']

            image_record.ma_uuid = ma_uuid

            img_etag = result_obj['idigbio:data'].get('idigbio:imageEtag')

            if img_etag and image_record.md5 == img_etag:
                image_record.upload_time = datetime.utcnow()
                image_record.url = url
            else:
                raise ClientException('Upload failed because local MD5 does not match the eTag or no eTag is returned.')

            if conn.attempts > 1:
                logger.debug('%s [after %d attempts]' % (path, conn.attempts))
            else:
                logger.debug('%s [after %d attempts]' % (path, conn.attempts))
            
            fn = partial(ongoing_upload_task.increment, 'success_count')
            postprocess_queue.put(fn)
            
            fn = partial(ongoing_upload_task.check_continuous_fails, True)
            postprocess_queue.put(fn)
            
        except ClientException:
            logger.error("An object job failed.")
            fn = partial(ongoing_upload_task.increment, 'fails')
            ongoing_upload_task.postprocess_queue.put(fn)
            
            def _abort_if_necessary():
                if ongoing_upload_task.check_continuous_fails(False):
                    logger.info("Aborting threads because continuous failures exceed the threshold.")
                    map(lambda x: x.abort_thread(), ongoing_upload_task.object_threads)
            ongoing_upload_task.postprocess_queue.put(_abort_if_necessary)
            
            raise
        except OSError, err:
            if err.errno != ENOENT:
                raise
            error_queue.put('Local file %s not found' % repr(path))

    def _upload_dir(dir_path):
        allowed_files = re.compile(constants.ALLOWED_FILES, re.IGNORECASE)
        for dirpath, _dirnames, filenames in os.walk(dir_path):
            for filename in filenames:
                if not allowed_files.match(filename):
                    continue
                subpath = join(dirpath, filename)
                object_queue.put({'path': subpath})
                fn = partial(ongoing_upload_task.increment, 'total_count')
                postprocess_queue.put(fn)
        logger.info("All jobs to upload individual files are added to the job queue.")

    conn = get_conn()
    try:
        if resume:
            batch = model.load_last_batch()
            if batch.finish_time:
                raise IngestServiceException("Last batch already finished, why resume?")
            # Assign local variables with values in DB. 
            root_path = batch.root
            recordset_uuid = batch.recordset_uuid
        elif root_path:
            recordset_uuid = conn.post_recordset()
            batch = model.add_upload_batch(root_path, recordset_uuid)
            model.commit()
        else:
            raise IngestServiceException("Root path not specified.")
        
        ongoing_upload_task.batch = batch
        
        worker_thread_count = 1
        object_threads = [QueueFunctionThread(object_queue, _object_job,
            get_conn()) for _junk in xrange(worker_thread_count)]
        ongoing_upload_task.object_threads = object_threads
        
        for thread in object_threads:
            thread.start()
        logger.debug('{0} upload worker threads started.'.format(worker_thread_count))

        if isdir(root_path):
            _upload_dir(root_path)
        else:
            # Single file.
            object_queue.put({'path': root_path})

        while not object_queue.empty():
            sleep(0.01)

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
