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
from dataingestion.services.user_config import get_user_config, set_user_config 
from dataingestion.services import api_client

singleton_task = BackgroundTaskQueue(cherrypy.engine, qsize=1, qwait=20)
singleton_task.subscribe()
singleton_task.start()
        
def _upload_task(root_path):
    authenticate(get_user_config('accountuuid'), get_user_config('apikey'))
    ingestion_manager.exec_upload_task(root_path)
    cherrypy.log("Upload task finished.",  __name__)

def _resume_task():
    authenticate(get_user_config('accountuuid'), get_user_config('apikey'))
    ingestion_manager.exec_upload_task(resume=True)
    cherrypy.log("Resume task finished.", __name__)

def start_upload(root_path):
    """
    Start the upload tasks and then return.
    
    :Return: True if a task is added to the queue. False if queue is full.
    """
    # Initial checks before the task is added to the queue.
    if not os.path.exists(root_path):
        raise ValueError("Root directory does not exist.")
    _start(_upload_task, root_path)
    
def start_resume():
    _start(_resume_task)

def _start(task, *args):
    try:
        return singleton_task.put(task, *args)
    except Queue.Full:
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

def authenticate(accountuuid, apikey):
    if api_client.authenticate(accountuuid, apikey):
        set_user_config('accountuuid', accountuuid)
        set_user_config('apikey', apikey)
    else:
        raise ValueError('Wrong authentication combination.')

def authenticated():
    try:
        authenticate(get_user_config('accountuuid'), get_user_config('apikey'))
        return True
    except AttributeError, ValueError:
        return False