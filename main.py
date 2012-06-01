#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
from os.path import dirname, realpath, join, exists
import sys, os, logging, site
current_dir = os.path.abspath(os.getcwd())
site.addsitedir(join(current_dir, "lib"))
import appdirs
import cherrypy
from cherrypy import engine
from dataingestion.ui.ingestui import DataIngestionUI
from dataingestion.services.ingest_rest import DataIngestionService
import dataingestion.services.model

APP_NAME = 'iDigBioDataIngestion'
APP_AUTHOR = 'iDigBio'
debug_mode = False

def main(argv):
    
    # process configuration files:
    engine_conf_path = os.path.join(current_dir, 'etc', 'engine.conf')
    cherrypy.config.update({"tools.staticdir.root": current_dir + "/www"})
    
    cherrypy.tree.mount(DataIngestionUI(), '/', config=engine_conf_path)
    cherrypy.tree.mount(DataIngestionService(), '/services', config=engine_conf_path)
    
    # process command-line arguments:
    if "--debug" in argv or "-d" in argv:
        debug_mode = True
        log_level = logging.DEBUG
    else:
        debug_mode = False
        log_level = logging.WARNING
        cherrypy.config.update({"environment": "production"})
    
    # configure the logging mechanisms
    logging.getLogger().setLevel(log_level)
    logging.getLogger("cherrypy").setLevel(log_level) # cherrypy must be forced
    svc_log = logging.getLogger('iDigBioSvc')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s - %(message)s'))
    svc_log.addHandler(handler)
    
    # configure the local sqlite database
    db_folder = appdirs.user_cache_dir(APP_NAME, APP_AUTHOR)
    if not exists(db_folder):
        os.makedirs(db_folder)
    db_file = join(db_folder, "idigbio.ingest.db")
    cherrypy.log.error("Use DB file: {0}".format(db_file), "main")
    dataingestion.services.model.setup(db_file)
    
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    cherrypy.log("Starting...")
    
    engine.start()
    if not debug_mode:
        # In a proper run, the text written here will be the only text output
        # the end-user sees: Keep it short and simple.
        print("Starting the iDigBio Data Ingestion Tool...")
        try:
            import webbrowser
            webbrowser.open("http://127.0.0.1:8080")
        except ImportError:
            # Gracefully fall back
            print("Open http://127.0.0.1:8080 in your webbrowser.")
        print("Close this window or hit ctrl+c to stop the local iDigBio Data "
              "Ingestion Tool.")
    engine.block()

if __name__ == '__main__':
    main(sys.argv)
