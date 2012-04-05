#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

from idigbio.swift import *
import ConfigParser
from os.path import join

container = 'dataingestor_test0'

options = None
object_queue = None

file_map = {}

def setup(conf_path):
    global options
    clientconf = ConfigParser.ConfigParser()
    clientconf.read(conf_path)
    
    class Object(object):
        pass
    
    options = Object()
    options.verbose = True
    options.leave_segments = False
    options.changed = True
    
    options.auth = clientconf.get('swift-client', 'auth')
    options.user = clientconf.get('swift-client', 'user')
    options.key = clientconf.get('swift-client', 'key')
    
    options.segment_size = None
    options.snet = False
    options.auth_version = '1.0'
    
def get_progress():
    """
    Return (total items, remaining items).
    """
    if object_queue is None:
        raise ValueError("Upload has not started yet.")
    
    return len(file_map), object_queue.qsize()
    
    
def upload(root_path):
    if options is None:
        raise ValueError("This module hasn't been setup yet.")
    
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
        except (ClientException, HTTPException, socket.error), err:
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
    global object_queue
    
    args = [container, root_path]
    
    object_queue = Queue(10000)

    def _segment_job(job, conn):
        if job.get('delete', False):
            conn.delete_object(job['container'], job['obj'])
        else:
            fp = open(job['path'], 'rb')
            fp.seek(job['segment_start'])
            conn.put_object(job.get('container', args[0] + '_segments'),
                job['obj'], fp, content_length=job['segment_size'])
        if options.verbose and 'log_line' in job:
            if conn.attempts > 1:
                print_queue.put('%s [after %d attempts]' %
                                (job['log_line'], conn.attempts))
            else:
                print_queue.put(job['log_line'])

    def _object_job(job, conn):
        path = job['path']
        container = job.get('container', args[0])
        dir_marker = job.get('dir_marker', False)
        try:
            obj = path
            if obj.startswith('./') or obj.startswith('.\\'):
                obj = obj[2:]
            if obj.startswith('/'):
                obj = obj[1:]
            put_headers = {'x-object-meta-mtime': str(getmtime(path))}
            if dir_marker:
                if options.changed:
                    try:
                        headers = conn.head_object(container, obj)
                        ct = headers.get('content-type')
                        cl = int(headers.get('content-length'))
                        et = headers.get('etag')
                        mt = headers.get('x-object-meta-mtime')
                        if ct.split(';', 1)[0] == 'text/directory' and \
                                cl == 0 and \
                                et == 'd41d8cd98f00b204e9800998ecf8427e' and \
                                mt == put_headers['x-object-meta-mtime']:
                            return
                    except ClientException, err:
                        if err.http_status != 404:
                            raise
                conn.put_object(container, obj, '', content_length=0,
                                content_type='text/directory',
                                headers=put_headers)
            else:
                # We need to HEAD all objects now in case we're overwriting a
                # manifest object and need to delete the old segments
                # ourselves.
                old_manifest = None
                if options.changed or not options.leave_segments:
                    try:
                        headers = conn.head_object(container, obj)
                        cl = int(headers.get('content-length'))
                        mt = headers.get('x-object-meta-mtime')
                        if options.changed and cl == getsize(path) and \
                                mt == put_headers['x-object-meta-mtime']:
                            return
                        if not options.leave_segments:
                            old_manifest = headers.get('x-object-manifest')
                    except ClientException, err:
                        if err.http_status != 404:
                            raise
                if options.segment_size and \
                        getsize(path) < options.segment_size:
                    full_size = getsize(path)
                    segment_queue = Queue(10000)
                    segment_threads = [QueueFunctionThread(segment_queue,
                        _segment_job, create_connection()) for _junk in
                        xrange(10)]
                    for thread in segment_threads:
                        thread.start()
                    segment = 0
                    segment_start = 0
                    while segment_start < full_size:
                        segment_size = int(options.segment_size)
                        if segment_start + segment_size > full_size:
                            segment_size = full_size - segment_start
                        segment_queue.put({'path': path,
                            'obj': '%s/%s/%s/%08d' % (obj,
                                put_headers['x-object-meta-mtime'], full_size,
                                segment),
                            'segment_start': segment_start,
                            'segment_size': segment_size,
                            'log_line': '%s segment %s' % (obj, segment)})
                        segment += 1
                        segment_start += segment_size
                    while not segment_queue.empty():
                        sleep(0.01)
                    for thread in segment_threads:
                        thread.abort = True
                        while thread.isAlive():
                            thread.join(0.01)
                    if put_errors_from_threads(segment_threads, error_queue):
                        raise ClientException('Aborting manifest creation '
                            'because not all segments could be uploaded. %s/%s'
                            % (container, obj))
                    new_object_manifest = '%s_segments/%s/%s/%s/' % (
                        container, obj, put_headers['x-object-meta-mtime'],
                        full_size)
                    if old_manifest == new_object_manifest:
                        old_manifest = None
                    put_headers['x-object-manifest'] = new_object_manifest
                    conn.put_object(container, obj, '', content_length=0,
                                    headers=put_headers)
                else:
                    conn.put_object(container, obj, open(path, 'rb'),
                        content_length=getsize(path), headers=put_headers)
                    
                    # Sleep a while after each upload to slow down the rate
                    # for demo purpose.
                    sleep(4)
                    
                if old_manifest:
                    segment_queue = Queue(10000)
                    scontainer, sprefix = old_manifest.split('/', 1)
                    for delobj in conn.get_container(scontainer,
                                                     prefix=sprefix)[1]:
                        segment_queue.put({'delete': True,
                            'container': scontainer, 'obj': delobj['name']})
                    if not segment_queue.empty():
                        segment_threads = [QueueFunctionThread(segment_queue,
                            _segment_job, create_connection()) for _junk in
                            xrange(10)]
                        for thread in segment_threads:
                            thread.start()
                        while not segment_queue.empty():
                            sleep(0.01)
                        for thread in segment_threads:
                            thread.abort = True
                            while thread.isAlive():
                                thread.join(0.01)
                        put_errors_from_threads(segment_threads, error_queue)
            if options.verbose:
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
        names = listdir(path)
        if not names:
            object_queue.put({'path': path, 'dir_marker': True})
        else:
            for name in listdir(path):
                subpath = join(path, name)
                if isdir(subpath):
                    _upload_dir(subpath)
                else:
                    object_queue.put({'path': subpath})
                    # Add an entry to files_map to track progress
                    file_map[subpath] = ''

    create_connection = lambda: get_conn(options)
    object_threads = [QueueFunctionThread(object_queue, _object_job,
        create_connection()) for _junk in xrange(10)]
    for thread in object_threads:
        thread.start()
    conn = create_connection()
    # Try to create the container, just in case it doesn't exist. If this
    # fails, it might just be because the user doesn't have container PUT
    # permissions, so we'll ignore any error. If there's really a problem,
    # it'll surface on the first object PUT.
    try:
        conn.put_container(args[0])
        if options.segment_size is not None:
            conn.put_container(args[0] + '_segments')
    except ClientException, err:
        msg = ' '.join(str(x) for x in (err.http_status, err.http_reason))
        if err.http_response_content:
            if msg:
                msg += ': '
            msg += err.http_response_content[:60]
        error_queue.put(
            'Error trying to create container %r: %s' % (args[0], msg))
    except Exception, err:
        error_queue.put(
            'Error trying to create container %r: %s' % (args[0], err))
    try:
        for arg in args[1:]:
            if isdir(arg):
                _upload_dir(arg)
            else:
                object_queue.put({'path': arg})
        while not object_queue.empty():
            sleep(0.01)
        for thread in object_threads:
            thread.abort = True
            while thread.isAlive():
                thread.join(0.01)
        put_errors_from_threads(object_threads, error_queue)
    except ClientException, err:
        if err.http_status != 404:
            raise
        error_queue.put('Account not found')