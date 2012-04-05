#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php 
import time
from idigbio.storage.dataingestion.task_queue import BackgroundTaskQueue
import cherrypy
import Queue
import swiftclient

singleton_task = BackgroundTaskQueue(cherrypy.engine, qsize=1, qwait=20)
singleton_task.subscribe()
singleton_task.start()

progress = 0
def sleep_task():
    global progress
    while (progress < 100):
        time.sleep(1)
        progress = progress + 1
        
        
def upload_task(root_path):
    global task_ongoing
    swiftclient.upload(root_path)
    cherrypy.log("Upload task finished.")
    task_ongoing = False

task_ongoing = False
def start_upload(root_path):
    """
    Return True if a task is added to the queue. False if queue is full.
    """
    global task_ongoing
    if task_ongoing:
        cherrypy.log("Task ongoing.")
        return False
    try:
        singleton_task.put(upload_task, root_path)
        task_ongoing = True
        return True
    except Queue.Full, ex:
        cherrypy.log("Task ongoing.")
        return False

def check_progress():
    return swiftclient.get_progress()