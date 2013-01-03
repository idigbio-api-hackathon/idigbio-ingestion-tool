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
from dataingestion.services import model, ingestion_manager, constants, api_client
from dataingestion.services.user_config import get_user_config, set_user_config, rm_user_config

singleton_task = BackgroundTaskQueue(cherrypy.engine, qsize=1, qwait=20)
singleton_task.subscribe()
singleton_task.start()

# Be careful tasktype is the first argument.
def _upload_task(tasktype, path):
    authenticate(get_user_config('accountuuid'), get_user_config('apikey'))
    if tasktype == constants.DIR_TYPE:
        ingestion_manager.exec_upload_task(path)
    else:
        ingestion_manager.exec_upload_csv_task(path)
    cherrypy.log("Upload task finished.",  __name__)

def _resume_task(tasktype):
    authenticate(get_user_config('accountuuid'), get_user_config('apikey'))
    if tasktype == constants.DIR_TYPE:
        ingestion_manager.exec_upload_task(resume=True)
    else:
        ingestion_manager.exec_upload_csv_task(resume=True)
    cherrypy.log("Resume task finished.", __name__)

def start_upload(path, tasktype):
    """
    Start the upload tasks and then return.
    :Return: True if a task is added to the queue. False if queue is full.
    """
    # Initial checks before the task is added to the queue.
    if not os.path.exists(path):
        raise ValueError("Path does not exist.")
    _start(_upload_task, tasktype, path)

def start_resume(tasktype):
    _start(_resume_task, tasktype)

def _start(task, tasktype, *args):
    try:
        return singleton_task.put(task, tasktype, *args)
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
        return dict(path=batch.path, start_time=str(batch.start_time),
                    finished=(batch.finish_time and True or False), tasktype=batch.batchtype)
    else:
        return dict()

def authenticate(accountuuid, apikey):
    if api_client.authenticate(accountuuid, apikey):
        set_user_config('accountuuid', accountuuid)
        set_user_config('apikey', apikey)
    else:
        raise ValueError('Wrong authentication combination.')

# Check if it is authenticated.
def authenticated():
    try:
#        cherrypy.log.error("ingest_service.authenticated")
        authenticate(get_user_config('accountuuid'), get_user_config('apikey'))
        return True
    except (AttributeError, ValueError):
        return False
