#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
from os.path import dirname, realpath, join, exists
import sys, cherrypy, os, logging, site
current_dir = dirname(realpath(__file__))
site.addsitedir(join(current_dir, "lib"))
import appdirs
from cherrypy import engine
from idigbio.storage.dataingestion.ui.ingestui import DataIngestionUI
from idigbio.storage.dataingestion.services.ingest_rest import DataIngestionService
import idigbio.storage.dataingestion.services.model

APP_NAME = 'iDigBioDataIngestion'
APP_AUTHOR = 'iDigBio'

def main(argv):
    
#    cherrypy.clientconf.update(join(current_dir, 'etc', 'http.conf'))
    engine_conf_path = os.path.join(current_dir, 'etc', 'engine.conf')
    
    cherrypy.tree.mount(DataIngestionUI(), '/', config=engine_conf_path)
    cherrypy.tree.mount(DataIngestionService(), '/services', config=engine_conf_path)
    
    svc_log = logging.getLogger('iDigBioSvc')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s - %(message)s'))
    svc_log.addHandler(handler)
    svc_log.setLevel(logging.DEBUG)
    
    db_folder = appdirs.user_cache_dir(APP_NAME, APP_AUTHOR)
    if not exists(db_folder):
        os.mkdir(db_folder)
    db_file = join(db_folder, "idigbio.ingest.db")
    cherrypy.log.error("Use DB file: {0}".format(db_file), "main")
    idigbio.storage.dataingestion.services.model.setup(db_file)
    
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    cherrypy.log("Starting...")
    
    engine.start()
    engine.block()

if __name__ == '__main__':
    main(sys.argv)