#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This is the service module that the web service front-end calls to serve data
upload requests.
""" 
import cherrypy
import Queue, os
from dataingestion.task_queue import BackgroundTaskQueue
from dataingestion.services import model, ingestion_manager

singleton_task = BackgroundTaskQueue(cherrypy.engine, qsize=1, qwait=20)
singleton_task.subscribe()
singleton_task.start()
        
def upload_task(root_path):
    ingestion_manager.exec_upload_task(root_path)
    cherrypy.log("Upload task finished.")

def start_upload(root_path):
    """
    Start the upload tasks and then return.
    
    :Return: True if a task is added to the queue. False if queue is full.
    """
    
    # Initial checks before the task is added to the queue.
    if not os.path.exists(root_path):
        raise ValueError("Root directory does not exist.")
    
    try:
        return singleton_task.put(upload_task, root_path)
    except Queue.Full, ex:
        cherrypy.log("Task ongoing.")
        return False

def check_progress():
    return ingestion_manager.get_progress()

def get_result():
    return ingestion_manager.get_result()

def get_last_batch_info():
    '''
    Returns info about the last batch.
     
    :rtype: dict
    '''
    batch = model.load_last_batch()
    if batch:
        return dict(root=batch.root, start_time=str(batch.start_time),
                    finished=(batch.finish_time and True or False))
    else:
        return dict()
