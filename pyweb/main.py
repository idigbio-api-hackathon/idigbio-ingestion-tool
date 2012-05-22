#!/usr/bin/env python
#
# Copyright (c) 2011 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
import sys, cherrypy, os, logging, tempfile
from os.path import dirname, realpath, join
from idigbio.storage.dataingestion.ui.ingestui import DataIngestionUI
from idigbio.storage.dataingestion.services.ingest_rest import DataIngestionService
import idigbio.storage.dataingestion.services.model 

current_dir = dirname(realpath(__file__))
#sys.path = [current_dir] + sys.path

def main(argv):
    
#    cherrypy.clientconf.update(join(current_dir, 'etc', 'http.conf'))
    engine_conf_path = os.path.join(current_dir, 'etc', 'engine.conf')
    
    cherrypy.tree.mount(DataIngestionUI(), '/', config=engine_conf_path)
    cherrypy.tree.mount(DataIngestionService(), '/services', config=engine_conf_path)
    
    svc_log = logging.getLogger('iDigBioSvc')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s - %(message)s'))
    svc_log.addHandler(handler)
    svc_log.setLevel(logging.INFO)
    
    db_file = join(tempfile.gettempdir(), "idigbio.ingest.db")
    idigbio.storage.dataingestion.services.model.setup(db_file)
    
    cherrypy.log("Starting...")
    cherrypy.engine.start()

if __name__ == '__main__':
    main(sys.argv)