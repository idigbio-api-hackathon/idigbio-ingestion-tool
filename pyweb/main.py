#!/usr/bin/env python
#
# Copyright (c) 2011 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
import sys, cherrypy, os
from os.path import dirname, join, realpath
from idigbio.storage.dataingestion.ui.ingestui import DataIngestionUI
from idigbio.storage.dataingestion.services.ingestservice import DataIngestionService
from idigbio.storage.dataingestion.services import swiftclient 

current_dir = dirname(realpath(__file__))
#sys.path = [current_dir] + sys.path

def main(argv):
    swiftclient.setup(join(current_dir, 'etc', 'swiftclient.conf'))
    
#    cherrypy.clientconf.update(join(current_dir, 'etc', 'http.conf'))
    engine_conf_path = os.path.join(current_dir, 'etc', 'engine.conf')
    
    ui = cherrypy.tree.mount(DataIngestionUI(), '/', config=engine_conf_path)
    svc = cherrypy.tree.mount(DataIngestionService(), '/services', config=engine_conf_path)
    cherrypy.log("Starting...")
    cherrypy.engine.start()
#    cherrypy.quickstart(Root(), '/', clientconf=engine_conf_path)

if __name__ == '__main__':
    main(sys.argv)