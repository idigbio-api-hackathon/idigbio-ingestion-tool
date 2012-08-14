#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module implements the data model for the service.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import ForeignKey
import logging
import hashlib
import argparse
from datetime import datetime
from sqlalchemy.sql.expression import desc

Base = declarative_base()

logger = logging.getLogger('iDigBioSvc.model')

def check_session(func):
    def wrapper(*args):
        if session is None:
            raise ValueError("DB session is None.")
        return func(*args)
    return wrapper

class ImageRecord(Base):
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True)
    path = Column(String)
    '''
    Path does not have to be unique as there can be multiple 
    unrelated */USBVolumne1/DCIM/Image1.JPG*s.
    '''
    mr_uuid = Column(String)
    '''
    The UUID of the *media record* for this image. 
    '''
    
    ma_uuid = Column(String)
    '''
    The UUID of the *media AP* for this image.
    '''
    
    md5 = Column(String, index=True, unique=True)
    comments = Column(String)
    upload_time = Column(DateTime)
    '''
    The UTC time measured by the local machine. 
    None if the image is not uploaded.
    '''
    url = Column(String)
    batch_id = Column(Integer, ForeignKey('batches.id', onupdate="cascade"))

    def __init__(self, path, md5, batch):
        self.path = path
        self.md5 = md5
        self.batch = batch

class UploadBatch(Base):
    '''
    Represents a batch which is the operation executed when the user clicks the 
    "Upload" button. 
    
    .. note:: When a batch fails and is resumed, the same batch record and 
       recordset id are reused.
       
    '''
    __tablename__ = 'batches'

    id = Column(Integer, primary_key=True)
    root = Column(String)
    '''
    The root path for the batch upload.
    '''
    recordset_uuid = Column(String)
    copyright_license = Column(String)
    start_time = Column(DateTime)
    '''
    The local time at which the batch task starts.
    '''
    finish_time = Column(DateTime)
    '''
    The local time that the batch upload finishes. None if it is not successfully
    finished.
    '''
    images = relationship(ImageRecord, backref="batch")
    '''
    All images associated with this batch.
    '''

    def __init__(self, root, recordset_uuid, start_time, license_):
        self.root = root
        self.recordset_uuid = recordset_uuid
        self.start_time = start_time
        self.copyright_license = license_

session = None

def setup(db_file):
    global session

    db_conn = "sqlite:///%s" % db_file
    logger.info("DB Connection: %s" % db_conn)
    engine = create_engine(db_conn, connect_args={'check_same_thread':False})
    engine.Echo = True
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

def md5_file(f, block_size=2 ** 20):
    md5 = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()

@check_session
def add_or_load_image(batch, path):
    '''
    Return the image or None is the image should not be uploaded.
    
    :rtype: ImageRecord or None.
    .. note:: Image identity is not determined by path but rather by its MD5.
    '''
    with open(path, 'rb') as f:
        md5 = md5_file(f)
    record = session.query(ImageRecord).filter_by(md5=md5).first()
    if record is None:
        return add_image(batch, path)
        # What if the file at the same path is actually new?
    elif record.upload_time:
        # Already uploaded.
        return None
    else:
        # Needs to be uplaoded.
        return record

@check_session
def add_image(batch, path):
    with open(path, 'rb') as f:
        md5 = md5_file(f)

    record = ImageRecord(path, md5, batch)
    session.add(record)
    logger.debug("Image %s added to DB session." % path)
    return record

@check_session
def add_upload_batch(root, recordset_uuid, license_):
    start_time = datetime.now()
    batch = UploadBatch(root, recordset_uuid, start_time, license_)
    session.add(batch)
    return batch

@check_session
def count_batch_size(batch_id):
    batch_id = int(batch_id)
    query = session.query(UploadBatch).filter_by(id=batch_id).join(UploadBatch.images)
    return query.count()

@check_session
def get_batch_details(batch_id):
    batch_id = int(batch_id)
    query = session.query(ImageRecord.path, ImageRecord.url).filter_by(batch_id=batch_id)
    return query.all()

@check_session
def load_last_batch():
    batch = session.query(UploadBatch).order_by(desc(UploadBatch.id)).first()
    return batch

@check_session
def commit():
    logger.debug("Committing session to DB.")
    session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("db")
    parser.add_argument("method")
    parser.add_argument("arguments", nargs='*')
    args = parser.parse_args()

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    setup(args.db)
    m = globals()[args.method]
    print m(*args.arguments)

if __name__ == '__main__':
    main()
