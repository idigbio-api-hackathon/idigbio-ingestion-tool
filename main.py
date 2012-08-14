#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
from os.path import dirname, realpath, join, exists
import sys, cherrypy, os, logging, site
from datetime import datetime
import argparse
import shutil
current_dir = dirname(realpath(__file__))
site.addsitedir(join(current_dir, "lib"))
import appdirs
import ConfigParser
from cherrypy import engine
from dataingestion.ui.ingestui import DataIngestionUI
from dataingestion.services.ingest_rest import DataIngestionService
import dataingestion.services.model

APP_NAME = 'iDigBio.DataIngestion'
APP_AUTHOR = 'iDigBio'

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--newdb", action="store_true", help='create a new db file')
    parser.add_argument("-v", "--verbose", action="store_true", help='log debug information')
    args = parser.parse_args()
    
    # Configure modules.
    idigbio_conf_path = join(current_dir, 'etc', 'idigbio.conf')
    config = ConfigParser.ConfigParser()
    config.read(idigbio_conf_path)
    api_endpoint = config.get('iDigBio', 'idigbio.api_endpoint')
    dataingestion.services.api_client.init(api_endpoint)
    cherrypy.config.update(join(current_dir, 'etc', 'http.conf'))
    engine_conf_path = join(current_dir, 'etc', 'engine.conf')
    cherrypy.tree.mount(DataIngestionUI(), '/', config=engine_conf_path)
    cherrypy.tree.mount(DataIngestionService(), '/services', config=engine_conf_path)
    
    # Set up logging
    svc_log = logging.getLogger('iDigBioSvc')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(thread)d %(name)s %(levelname)s - %(message)s'))
    svc_log.addHandler(handler)
    log_folder = appdirs.user_log_dir(APP_NAME, APP_AUTHOR)
    if not exists(log_folder):
        os.makedirs(log_folder)
    log_file = join(log_folder, "idigbio.ingest.{0}.log".format(datetime.now().strftime("%Y-%b-%d_%H-%M-%S")))
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter('%(asctime)s %(thread)d %(name)s %(levelname)s - %(message)s'))
    svc_log.addHandler(handler)
    if args.verbose:
        svc_log.setLevel(logging.DEBUG)
    else:
        svc_log.setLevel(logging.INFO)
    
    # Set up DB.
    data_folder = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
    if not exists(data_folder):
        os.makedirs(data_folder)
    db_file = join(data_folder, "idigbio.ingest.db")
    if args.newdb and exists(db_file):
        move_to = join(data_folder, "idigbio.ingest." + datetime.now().strftime("%Y-%b-%d_%H-%M-%S") + ".db")
        shutil.move(db_file, move_to)
        cherrypy.log.error("Creating a new db. Moved the old DB to {0}".format(move_to), "main")
    cherrypy.log.error("Use DB file: {0}".format(db_file), "main")
    dataingestion.services.model.setup(db_file)
    
    # Set up/start server.
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    cherrypy.log("Starting...", "main")
    engine.start()
    engine.block()

if __name__ == '__main__':
    main(sys.argv)