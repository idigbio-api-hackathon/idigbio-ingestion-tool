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
from datetime import datetime

# From swift bin
from Queue import Empty, Queue
from threading import enumerate as threading_enumerate, Thread
from time import sleep
from sys import argv, exc_info, exit, stderr, stdout
from os.path import basename, dirname, getmtime, getsize, isdir, join
from traceback import format_exception
from errno import EEXIST, ENOENT
from api_client import ClientException, Connection
import model

logger = logging.getLogger('iDigBioSvc.client_manager')

object_queue = None
""" The queue for the objects to be uploaded. """

def get_conn():
    return Connection()

###
# Code copied verbatim from swift
###

def put_errors_from_threads(threads, error_queue):
    """
    Places any errors from the threads into error_queue.
    :param threads: A list of QueueFunctionThread instances.
    :param error_queue: A queue to put error strings into.
    :returns: True if any errors were found.
    """
    was_error = False
    for thread in threads:
        for info in thread.exc_infos:
            was_error = True
            if isinstance(info[1], ClientException):
                error_queue.put(str(info[1]))
            else:
                error_queue.put(''.join(format_exception(*info)))
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
                logger.error("Task failed in a worker thread.")
                self.exc_infos.append(exc_info())
###
# End code copied verbatim from swift
###
    
batch = None
total_count = 0
def get_progress():
    """
    Return (total items, remaining items).
    """
    if object_queue is None:
        raise ValueError("Upload has not started yet.")
    
    return total_count or object_queue.qsize(), object_queue.qsize()
    
def upload(root_path):
    # Modified from swift.__main__
    print_queue = Queue(10000)

    def _print(item):
        if isinstance(item, unicode):
            item = item.encode('utf8')
        print item

    print_thread = QueueFunctionThread(print_queue, _print)
    print_thread.start()

    error_queue = Queue(10000)

    def _error(item):
        if isinstance(item, unicode):
            item = item.encode('utf8')
        print >> stderr, item

    error_thread = QueueFunctionThread(error_queue, _error)
    error_thread.start()

    try:
        try:
            _st_upload(root_path, print_queue, error_queue)
        except ClientException, err:
            error_queue.put(str(err))
        while not print_queue.empty():
            sleep(0.01)
        print_thread.abort = True
        while print_thread.isAlive():
            print_thread.join(0.01)
        while not error_queue.empty():
            sleep(0.01)
        error_thread.abort = True
        while error_thread.isAlive():
            error_thread.join(0.01)
    except (SystemExit, Exception):
        for thread in threading_enumerate():
            thread.abort = True
        raise
    
    
def _st_upload(root_path, print_queue, error_queue):
    """
    Copied from swift/bin/swift.st_upload
    """
    global object_queue, batch
    
    object_queue = Queue(10000)

    def _object_job(job, conn):
        path = job['path']
        
        try:
            obj = path
            image_record = model.add_image(batch, path)
            
            record_uuid = conn.post_mediarecord(recordset_uuid)
            image_record.uuid = record_uuid
            
            conn.post_media(obj, record_uuid)
            image_record.upload_time = datetime.utcnow()
            
            # Sleep a while after each upload to slow down the rate
            # for demo purpose.
#            sleep(4)
                    
            if conn.attempts > 1:
                print_queue.put(
                    '%s [after %d attempts]' % (obj, conn.attempts))
            else:
                print_queue.put(obj)
        except OSError, err:
            if err.errno != ENOENT:
                raise
            error_queue.put('Local file %s not found' % repr(path))

    def _upload_dir(path):
        global total_count
        for dirpath, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                subpath = join(dirpath, filename)
                object_queue.put({'path': subpath})
                total_count += 1

    object_threads = [QueueFunctionThread(object_queue, _object_job,
        get_conn()) for _junk in xrange(10)]
    for thread in object_threads:
        thread.start()
    logger.debug('Upload worker threads started.')
    
    conn = get_conn()
    try:
        recordset_uuid = conn.post_recordset()
        batch = model.add_upload_batch(root_path, recordset_uuid)
        model.commit()
        
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
                
        was_error = put_errors_from_threads(object_threads, error_queue)
        if not was_error:
            logger.info("Upload finishes with no error")
            batch.finish_time = datetime.utcnow()
        else:
            logger.error("Upload finishes with errors.")
        
    except ClientException, err:
        if err.http_status != 404:
            raise
        error_queue.put('Upload failed.')
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
    upload(args.root_path)
    
if __name__ == '__main__':
    main()