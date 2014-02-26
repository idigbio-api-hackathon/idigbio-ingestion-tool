#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This module implements the result file generation functionalities.
"""

import os, logging, csv
from dataingestion.services import constants, model

logger = logging.getLogger('iDigBioSvc.csv_saver')

def save_all(target_path):
  result = model.get_all_success_details()
  if not result:
    print "No information found."
    return None

  # Make the outputstream for stub_csv_path.
  csv_headerline = model.get_batch_details_fieldnames()

  with open(target_path, 'wb') as f:
    csv_writer = csv.writer(f, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_ALL)
    csv_writer.writerow(csv_headerline)
    csv_writer.writerows(result)

  return target_path
