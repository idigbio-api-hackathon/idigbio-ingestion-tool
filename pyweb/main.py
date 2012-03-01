#!/usr/bin/env python
#
# Copyright (c) 2011 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
import sys, runpy, cherrypy
from os.path import dirname, join, realpath
from idigbio.storage.importer.web.webapp import HelloWorld
 
def prep_syspath():
    REPO_ROOT = dirname(realpath(__file__))
    EXTRA_PATHS = [REPO_ROOT, join(REPO_ROOT, "lib")]
    sys.path = EXTRA_PATHS + sys.path

def main(argv):
    prep_syspath()
    cherrypy.quickstart(HelloWorld(), '/', config='cherrypy.config')

if __name__ == '__main__':
    main(sys.argv)