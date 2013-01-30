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

__images_tablename__ = 'imagesV3'
__batches_tablename__ = 'batchesV3'

Base = declarative_base()

logger = logging.getLogger('iDigBioSvc.model')

def check_session(func):
    def wrapper(*args):
        if session is None:
            raise ValueError("DB session is None.")
        return func(*args)
    return wrapper

class ImageRecord(Base):
    __tablename__ = __images_tablename__

    id = Column(Integer, primary_key=True)
    path = Column(String)
    '''
    Path does not have to be unique as there can be multiple 
    unrelated */USBVolumne1/DCIM/Image1.JPG*s.
    '''
    file_exist = Column(Boolean)
    '''
    Indicates if the given path is a valid file.
    '''

    providerid = Column(String)
    '''
    providerid is unique for each media record within the record set.
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
    '''
    This md5 is got from "record set uuid + CSV record line + media file hash".
    '''

    comments = Column(String)
    upload_time = Column(DateTime)
    '''
    The UTC time measured by the local machine. 
    None if the image is not uploaded.
    '''
    url = Column(String)

    mr_record = Column(String)
    '''
    MadiaRecord record in JSON String
    '''
    ma_record = Column(String)
    '''
    MadiaAP record in JSON String
    '''
    
    batch_id = Column(Integer, ForeignKey(__batches_tablename__+'.id', onupdate="cascade"))

    def __init__(self, path, pid, md5, exist, batch):
        self.path = path
        self.providerid = pid
        self.md5 = md5
        self.file_exist = exist
        self.batch_id = batch.id

class UploadBatch(Base):
    '''
    Represents a batch which is the operation executed when the user clicks the 
    "Upload" button. 
    
    .. note:: When a batch fails and is resumed, the same batch record and 
       recordset id are reused.
    '''
    __tablename__ = __batches_tablename__

    id = Column(Integer, primary_key=True)
    path = Column(String)
    '''
    The path for the batch upload.
    '''
    recordset_uuid = Column(String)
    start_time = Column(DateTime)
    '''
    The local time at which the batch task starts.
    '''
    finish_time = Column(DateTime)
    '''
    The local time that the batch upload finishes. None if it is not successfully
    finished.
    '''
    batchtype = Column(String)
    '''
    The type of the batch task, it can be "dir" or "csv".
    '''
    md5 = Column(String)
    '''
    The md5 of the CSV file + uuid.
    '''

    images = relationship(ImageRecord, backref="batch")
    '''
    All images associated with the batches in the table.
    '''

    def __init__(self, path, recordset_uuid, start_time, md5, batchtype):
        self.path = path
        self.recordset_uuid = recordset_uuid
        self.start_time = start_time
        self.md5 = md5
        self.batchtype = batchtype

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
    return md5

def generate_record(csvrow, rs_uuid):
    mediapath, mediaproviderid = csvrow
    mediapath = mediapath.strip(' ')
    mediaproviderid = mediaproviderid.strip(' ')
    recordmd5 = hashlib.md5()
    recordmd5.update(rs_uuid)
    recordmd5.update(mediapath)
    recordmd5.update(mediaproviderid)
    return mediapath, mediaproviderid, recordmd5

# decorator
@check_session
def add_or_load_image(batch, csvrow, rs_uuid, tasktype):
    '''
    Return the image or None is the image should not be uploaded.
    
    :rtype: ImageRecord or None.
    .. note:: Image identity is not determined by path but rather by its MD5.
    '''
    path, mediaproviderid, md5value = generate_record(csvrow, rs_uuid)

    file_found = True
    try:
        with open(path, 'rb') as f:
            filemd5 = md5_file(f)
        md5value.update(filemd5.hexdigest())
    except IOError as err:
        logger.debug("The file "+path+" cannot be found.")
        file_found = False

    record = session.query(ImageRecord).filter_by(md5=md5value.hexdigest()).first()
    if record is None: # No duplicate record.
        return add_image(batch, path, mediaproviderid, md5value, file_found)
    elif record.upload_time: # Found the duplicate record, already uploaded.
        record.batchid = batch.id 
        return None
    else: # Found the duplicate record, but not uploaded.
        if file_found == True: # Needs to be uploaded.
            return record
        else: # No need to be uploaded, because the file does not exist.
            record.batchid = batch.id 
            # Update the batch id so that you can find the complete result of this batch.
            return record


@check_session
def add_image(batch, path, providerid, md5value, exist):
    record = ImageRecord(path, providerid, md5value.hexdigest(), exist, batch)
    session.add(record)
    logger.debug("Image %s added to DB session." % path)
    return record

@check_session
def add_upload_batch(path, recordset_uuid, tasktype):
    start_time = datetime.now()
    with open(path, 'rb') as f:
        md5value = md5_file(f)
    md5value.update(recordset_uuid)

    record = session.query(UploadBatch).filter_by(md5=md5value.hexdigest()).first()
    if record is None: # No duplicate record.
        batch = UploadBatch(path, recordset_uuid, start_time, md5value.hexdigest(), tasktype)
        session.add(batch)
        return batch
    return record # Otherwise, just return the existing record. You still need to process it.

@check_session
def get_imagerecords_by_batchid(batch_id):
    batch_id = int(batch_id)
    imagerecords = session.query(ImageRecord).filter_by(batch_id=batch_id)
    return imagerecords

@check_session
def count_batch_size(batch_id):
    batch_id = int(batch_id)
    query = session.query(UploadBatch).filter_by(id=batch_id).join(UploadBatch.images)
    return query.count()

@check_session
def get_batch_details(batch_id):
    batch_id = int(batch_id)
    query = session.query(ImageRecord.path, ImageRecord.file_exist, ImageRecord.url).filter_by(batch_id=batch_id)
    return query.all()

@check_session
def load_last_batch():
    batch = session.query(UploadBatch).order_by(desc(UploadBatch.id)).first()
    return batch

@check_session
def commit():
    logger.debug("Committing session to DB.")
    session.commit()

def close():
    global session
    if session:
        session.close()
        session = None

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
