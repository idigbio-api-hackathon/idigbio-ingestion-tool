#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
from os.path import join, exists
import sys, os, logging, site
import atexit
import logging.handlers
from datetime import datetime
import argparse
import shutil
current_dir = os.path.abspath(os.getcwd())
site.addsitedir(join(current_dir, "lib"))
import appdirs
import cherrypy
import ConfigParser
from cherrypy import engine
from dataingestion.ui.ingestui import DataIngestionUI
from dataingestion.services.ingest_rest import DataIngestionService
import dataingestion.services.model
import dataingestion.services.user_config

APP_NAME = 'iDigBio Data Ingestion Tool'
APP_AUTHOR = 'iDigBio'
debug_mode = False
quiet_mode = False

USER_CONFIG_FILENAME = 'user.conf'

def main(argv):    
    # Process configuration files and configure modules.
    idigbio_conf_path = join(current_dir, 'etc', 'idigbio.conf')
    config = ConfigParser.ConfigParser()
    config.read(idigbio_conf_path)
    api_endpoint = config.get('iDigBio', 'idigbio.api_endpoint')
    
    dataingestion.services.api_client.init(api_endpoint)
    cherrypy.config.update(join(current_dir, 'etc', 'http.conf'))
    
    engine_conf_path = join(current_dir, 'etc', 'engine.conf')
    cherrypy.config.update(engine_conf_path)
    cherrypy.config.update({"tools.staticdir.root": current_dir + "/www"})
    cherrypy.tree.mount(DataIngestionUI(), '/', config=engine_conf_path)
    cherrypy.tree.mount(DataIngestionService(), '/services',
                        config=engine_conf_path)
    
    # Process command-line arguments:
    parser = argparse.ArgumentParser()
    parser.add_argument("--newdb", action="store_true", help='create a new db file')
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    if args.debug:
        debug_mode = True
        log_level = logging.DEBUG
    else:
        debug_mode = False
        log_level = logging.WARNING
        cherrypy.config.update({"environment": "production"})
    
    if args.quiet:
        quiet_mode = True
        if debug_mode:
            raise Exception("The --quiet or -q flags are not intended to be "
                            "used with the --debug or -d flags.")
    else:
        quiet_mode = False

    # Configure the logging mechanisms
    # Default log level to DEBUG and filter the logs for console output.
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("cherrypy").setLevel(logging.INFO) # cherrypy must be forced
    svc_log = logging.getLogger('iDigBioSvc')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(thread)d %(name)s %(levelname)s - %(message)s'))
    # User-specified log level only controls console output.
    handler.setLevel(log_level)
    svc_log.addHandler(handler)
    log_folder = appdirs.user_log_dir(APP_NAME, APP_AUTHOR)
    if not exists(log_folder):
        os.makedirs(log_folder)
    log_file = join(log_folder, "idigbio.ingest.log")
    handler = logging.handlers.RotatingFileHandler(log_file, backupCount=10)
    handler.setFormatter(logging.Formatter('%(asctime)s %(thread)d %(name)s %(levelname)s - %(message)s'))
    handler.setLevel(logging.DEBUG)
    handler.doRollover()
    svc_log.addHandler(handler)
        
    # Set up the DB.
    data_folder = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
    if not exists(data_folder):
        os.makedirs(data_folder)
    db_file = join(data_folder, "idigbio.ingest.db")
    if args.newdb:
        _move_db(data_folder, db_file)
        cherrypy.log.error("Creating a new DB file.", "main")

    cherrypy.log.error("Use DB file: {0}".format(db_file), "main")
    dataingestion.services.model.setup(db_file)
    
    # Set up the user config.
    user_config_path = join(data_folder, USER_CONFIG_FILENAME)
    dataingestion.services.user_config.setup(user_config_path)
    
    # Set up/start server.
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    cherrypy.log("Starting...", "main")

    atexit.register(_logout_user_if_configured, user_config_path, data_folder, db_file)

    engine.start()
    if not debug_mode and not quiet_mode:
        # In a proper run, the text written here will be the only text output
        # the end-user sees: Keep it short and simple.
        print("Starting the iDigBio Data Ingestion Tool...")
        try:
            import webbrowser
            webbrowser.open("http://127.0.0.1:{0}".format(cherrypy.config['server.socket_port']))
        except ImportError:
            # Gracefully fall back
            print("Open http://127.0.0.1:{0} in your webbrowser.".format(cherrypy.config['server.socket_port']))
        print("Close this window or hit ctrl+c to stop the local iDigBio Data "
              "Ingestion Tool.")
    engine.block()

def _move_db(data_folder, db_file):
    if exists(db_file):
        dataingestion.services.model.close()    
        move_to = join(data_folder, "idigbio.ingest." + datetime.now().strftime("%Y-%b-%d_%H-%M-%S") + ".db")
        shutil.move(db_file, move_to)
        cherrypy.log.error("Moved the old DB to {0}".format(move_to), "main")

def _logout_user_if_configured(user_config_path, data_folder, db_file):
    logout = dataingestion.services.user_config.try_get_user_config('logoutafterexit')
    if logout == 'true':
        cherrypy.log.error("User chooses to log out after exit. Logging out...", "main")
        _move_db(data_folder, db_file)
        os.remove(user_config_path)

if __name__ == '__main__':
    main(sys.argv)
