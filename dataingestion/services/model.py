#!/usr/bin/env python
#
# Copyright (c) 2012 Xu, Jiang Yan <me@jxu.me>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module implements the data model for the service.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, types
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql.expression import desc
from sqlalchemy.types import TypeDecorator, Unicode
import logging, hashlib, argparse, os, time, struct, re
from datetime import datetime
from dataingestion.services import constants
#import pwd
#from PIL import Image
#from PIL.ExifTags import TAGS

__images_tablename__ = constants.IMAGES_TABLENAME
__batches_tablename__ = constants.BATCHES_TABLENAME

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
    file_error = Column(String)
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
    '''
    Comments.
    '''
    upload_time = Column(String)
    '''
    The UTC time measured by the local machine. 
    None if the image is not uploaded.
    '''
    url = Column(String)

    mr_record = Column(types.BLOB)
    '''
    MadiaRecord record in JSON String
    '''
    ma_record = Column(types.BLOB)
    '''
    MadiaAP record in JSON String
    '''
    description = Column(String)
    '''
    http://purl.org/dc/terms/description
    '''
    language_code = Column(String)
    '''
    http://purl.org/dc/terms/language
    '''
    title = Column(String)
    '''
    http://purl.org/dc/terms/title
    '''
    digitalization_device = Column(String)
    '''
    http://rs.tdwg.org/ac/terms/captureDevice
    '''
    pixel_resolution = Column(String)
    '''
    e.g., 128micrometer
    '''
    magnification = Column(String)
    '''
    4x, 100x
    '''
    ocr_output = Column(String)
    '''
    Output of the process of applying OCR to the multimedia object.
    '''
    ocr_tech = Column(String)
    '''
    Tesseract version 3.01 on Windows, latin character set.
    '''
    info_withheld = Column(String)
    '''
    http://rs.tdwg.org/dwc/terms/informationWithheld
    '''
    media_md5 = Column(String)
    '''
    Checksum of the media object accessible via MediaUrl, using MD5.
    '''
    mime_type = Column(String)
    '''
    Technical type (format) of digital multimedia object. 
    When using the image ingestion appliance, this is automatically filled based on the 
    extension of the filename.
    '''
    media_size = Column(String)
    '''
    Size in bytes of the multimedia resource accessible through the MediaUrl. 
    Derived from the object when using the ingestion appliance.
    '''
    file_ctime = Column(String)
    '''
    ProviderCreatedTimeStamp, Date and time when the record was originally created on the provider data management system.
    '''
    file_owner = Column(String)
    '''
    providerCreatedByGUID
    '''
    media_metadata = Column(types.BLOB)
    '''
    Blob of text containing metadata about the media (e.g., from EXIF, IPTC). 
    Derived from the object when using the ingestion appliance.
    '''
    mr_etag = Column(String)
    '''
    Returned by server.
    '''

    # Changed because batch_id may be changed to map to other elements in batch table.
    batch_id = Column(Integer)
    #batch_id = Column(Integer, ForeignKey(__batches_tablename__+'.id', onupdate="cascade"))

    def __init__(self, path, pid, r_md5, error, batch, 
        desc, lang, title, digi, pix, mag, ocr_output, ocr_tech, info_withheld, m_md5, mime_type,
        m_size, ctime, f_owner, metadata):
        self.path = path
        self.providerid = pid
        self.md5 = r_md5
        self.file_error = error
        self.batch_id = batch.id
        self.description = desc
        self.language_code = lang
        self.title = title
        self.digitalization_device = digi
        self.pixel_resolution = pix
        self.magnification = mag
        self.ocr_output = ocr_output
        self.ocr_tech = ocr_tech
        self.info_withheld = info_withheld
        self.media_md5 = m_md5
        self.mime_type = mime_type
        self.media_size = m_size
        self.file_ctime = ctime
        self.file_owner = f_owner
        self.media_metadata = metadata

class UploadBatch(Base):
    '''
    Represents a batch which is the operation executed when the user clicks the 
    "Upload" button. 
    
    .. note:: When a batch fails and is resumed, the same batch record and 
       recordset id are reused.
    '''
    __tablename__ = __batches_tablename__
    id = Column(Integer, primary_key=True)
    CSVfilePath = Column(String) # The path for the batch upload.
    iDigbioProvidedByGUID = Column(String) # Log in information.
    RightsLicense = Column(String) # The license key.
    RightsLicenseStatementUrl = Column(String)
    RightsLicenseLogoUrl = Column(String)
    RecordSetGUID = Column(String) # The GUID user provided for the record set.
    RecordSetUUID = Column(String) # Return from server.
    start_time = Column(DateTime) # The local time at which the batch task starts.
    finish_time = Column(DateTime) # The local time that the batch upload finishes. None if not successful.
    batchtype = Column(String) # The type of the batch task, it can be "dir" or "csv".
    md5 = Column(String) # The md5 of the CSV file + uuid.
    
    # images = relationship(ImageRecord, backref="batch") # All images associated with the batches in the table.
    
    # The following fields are optional.
    MediaContentKeyword = Column(String)
    iDigbioProviderGUID = Column(String)
    iDigbioPublisherGUID = Column(String)
    FundingSource = Column(String)
    FundingPurpose = Column(String)
    def __init__(self, path, loginID, license, licenseStatementUrl, licenseLogoUrl,
        rs_guid, rs_uuid, s_time, md5, btype, kw, proID, pubID, fs, fp):
        self.CSVfilePath = path
        self.iDigbioProvidedByGUID = loginID
        self.RightsLicense = license
        self.RightsLicenseStatementUrl = licenseStatementUrl
        self.RightsLicenseLogoUrl = licenseLogoUrl
        self.RecordSetGUID = rs_guid
        self.RecordSetUUID = rs_uuid
        self.start_time = s_time
        self.md5 = md5
        self.batchtype = btype
        self.MediaContentKeyword = kw
        self.iDigbioProviderGUID = proID
        self.iDigbioPublisherGUID = pubID
        self.FundingSource = fs
        self.FundingPurpose = fp

session = None

def setCSVFieldNames(headerline):
    orderlist = [] # The order of the input fields in constants.INPUT_CSV_FILENAMES.
    logger.debug("The format of input CSV file:")
    logger.debug(headerline)
    for elem in headerline:
        if elem in constants.INPUT_CSV_FIELDNAMES:
            orderlist.append(constants.INPUT_CSV_FIELDNAMES.index(elem))
        else:
            raise IngestServiceException("Field " + elem + " in the CSV input file is not supported.")
    if 0 not in orderlist:
        raise IngestServiceException("idigbio:OriginalFileName field is required but not provided \
            in the CSV input file.")
    if 1 not in orderlist:
        raise IngestServiceException("idigbio:MediaGUID field is required but not provided \
            in the CSV input file.")
    return orderlist

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

def generate_record(csvrow, orderlist, rs_uuid):
    logger.debug('generate_record')
    print(csvrow)
    print(orderlist)
    
    mediapath = ""
    mediaproviderid = ""
    desc = ""
    lang = ""
    title = ""
    digi = ""
    pix = ""
    mag = ""
    ocr_output = ""
    ocr_tech = ""
    info_withheld = ""
    file_error = None
    mime_type = ""
    media_size = ""
    ctime = ""
    owner = ""
    metadata = ""
    mbuffer = ""
    filemd5 = hashlib.md5()

    index = 0
    for elem in orderlist:
        if elem == 0:
            mediapath = csvrow[index]
        elif elem == 1:
            mediaproviderid = csvrow[index]
        elif elem == 2:
            desc = csvrow[index]
        elif elem == 3:
            lang = csvrow[index]
        elif elem == 4:
            title = csvrow[index]
        elif elem == 5:
            digi = csvrow[index]
        elif elem == 6:
            pix = csvrow[index]
        elif elem == 7:
            mag = csvrow[index]
        elif elem == 8:
            ocr_output = csvrow[index]
        elif elem == 9:
            ocr_tech = csvrow[index]
        elif elem == 10:
            info_withheld = csvrow[index]
        index = index + 1

    recordmd5 = hashlib.md5()
    recordmd5.update(rs_uuid)
    recordmd5.update(mediapath)
    recordmd5.update(mediaproviderid)
    recordmd5.update(desc)
    recordmd5.update(lang)
    recordmd5.update(title)
    recordmd5.update(digi)
    recordmd5.update(pix)
    recordmd5.update(mag)
    recordmd5.update(ocr_output)
    recordmd5.update(ocr_tech)
    recordmd5.update(info_withheld)

    allowed_files = re.compile(constants.ALLOWED_FILES, re.IGNORECASE)
    print("DDD")
    if not allowed_files.match(mediapath): # This file is not allowed.
        file_error = "File type unsupported."
    else:
        name = os.path.splitext(mediapath)[1].split('.')
        extension = name[len(name)-1].lower()
        mime_type = constants.EXTENSION_MEDIA_TYPES[extension]

        try:
            with open(mediapath, 'rb') as f:
                filemd5 = md5_file(f)
        except IOError as err:
            logger.debug("The file "+mediapath+" cannot be found.")
            file_error = "File not found."
        print("EEE")

    if file_error == None:
        recordmd5.update(filemd5.hexdigest())
        media_size = os.path.getsize(mediapath)
        ctime = time.ctime(os.path.getmtime(mediapath))

        #owner = pwd.getpwuid(os.stat(mediapath).st_uid)[0]
        #logger.debug('777')

        #exifinfo = Image.open(mediapath)._getexif()
        #logger.debug('888')
        #for tag, value in exifinfo.items():
        #    decoded = TAGS.get(tag, tag)
        #    metadata[decoded] = value
        #logger.debug('999')
        #mbuffer = str(metadata)
    #logger.debug('generate_record done')

    return (mediapath,mediaproviderid,recordmd5.hexdigest(),file_error,desc,lang,title,digi,pix,
        mag,ocr_output,ocr_tech,info_withheld,filemd5.hexdigest(),mime_type,media_size,ctime, 
        owner,mbuffer)

# decorator
@check_session
def add_or_load_image(batch, csvrow, orderlist, rs_uuid, tasktype):
    '''
    Return the image or None is the image should not be uploaded.
    :rtype: ImageRecord or None.
    .. note:: Image identity is not determined by path but rather by its MD5.
    '''
    #logger.debug('add_or_load_image')
    logger.debug("add_or_load_image")
    (mediapath,mediaproviderid,recordmd5,file_error,desc,lang,title,digi,pix,mag,ocr_output,ocr_tech,
        info_withheld,filemd5,mime_type,media_size,ctime,owner,metadata) = generate_record(csvrow, 
        orderlist, rs_uuid)

    logger.debug("add_or_load_image done")
    record = session.query(ImageRecord).filter_by(md5=recordmd5).first()
    if record is None: # New record. Add the record.
        record = ImageRecord(mediapath, mediaproviderid, recordmd5, file_error, batch, 
            desc, lang, title, digi, pix, mag, ocr_output, ocr_tech, info_withheld, filemd5, mime_type,
            media_size, ctime, owner, metadata)
        session.add(record)
        #logger.debug('add_or_load_image: new record added')
        return record
    elif record.upload_time: # Found the duplicate record, already uploaded.
        #record.batch_id = batch.id
        return None
    else: # Found the duplicate record, but not uploaded or file not found.
        record.batch_id = batch.id
        return record

@check_session
def add_upload_batch(path, loginID, license, licenseStatementUrl, licenseLogoUrl,
    recordset_guid, recordset_uuid, tasktype, keyword, proID, pubID, fundingSource, fundingPurpose):
    start_time = datetime.now()
    with open(path, 'rb') as f:
        md5value = md5_file(f)
    md5value.update(loginID)
    md5value.update(license)
    md5value.update(recordset_guid)
    md5value.update(recordset_uuid)
    md5value.update(keyword)
    md5value.update(proID)
    md5value.update(pubID)
    md5value.update(fundingSource)
    md5value.update(fundingPurpose)

    #record = session.query(UploadBatch).filter_by(md5=md5value.hexdigest()).first()
    
    # Always add new record.
    newrecord = UploadBatch(path, loginID, license, licenseStatementUrl, licenseLogoUrl,
        recordset_guid, recordset_uuid, start_time, md5value.hexdigest(), tasktype, 
        keyword, proID, pubID, fundingSource, fundingPurpose)
    session.add(newrecord)
    return newrecord
    '''
    if record is None: # No duplicate record.
        newrecord = UploadBatch(path, loginID, license, licenseStatementUrl, licenseLogoUrl,
            recordset_guid, recordset_uuid, start_time, md5value.hexdigest(), tasktype, 
            keyword, proID, pubID, fundingSource, fundingPurpose)
        session.add(newrecord)
        return newrecord
    else:
        record.id = record.id + 1
        session.add(newrecord)
        return record # Otherwise, just return the existing record + 1. You still need to process it.
    '''
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
    logger.debug("get_batch_details for batch #" + str(batch_id))
    
    query = session.query(
        ImageRecord.path, ImageRecord.file_error, ImageRecord.providerid, 
        ImageRecord.mr_uuid, ImageRecord.ma_uuid, ImageRecord.comments, ImageRecord.upload_time,
        ImageRecord.url, ImageRecord.description, ImageRecord.language_code, ImageRecord.title,
        ImageRecord.digitalization_device, ImageRecord.pixel_resolution, ImageRecord.magnification,
        ImageRecord.ocr_output, ImageRecord.ocr_tech, ImageRecord.info_withheld, ImageRecord.media_md5,
        ImageRecord.mime_type, ImageRecord.media_size, ImageRecord.file_ctime, ImageRecord.file_owner,
        ImageRecord.mr_etag, UploadBatch.RecordSetUUID, UploadBatch.iDigbioProvidedByGUID,
        UploadBatch.MediaContentKeyword, UploadBatch.FundingSource, UploadBatch.FundingPurpose,
        UploadBatch.iDigbioPublisherGUID, UploadBatch.RightsLicenseStatementUrl, 
        UploadBatch.RightsLicenseLogoUrl, UploadBatch.iDigbioProviderGUID, UploadBatch.RightsLicense, 
        UploadBatch.CSVfilePath, UploadBatch.RecordSetGUID, ImageRecord.batch_id
        ).filter(ImageRecord.batch_id == batch_id).filter(UploadBatch.id == batch_id
        ).order_by(ImageRecord.id) # 25 elements.
    
    logger.debug("Image record count: " + str(query.count()))
    logger.debug("get_batch_details done")
    #for item in query:
    #    for elem in item:
    #        logger.debug(elem)

    #query = session.query(ImageRecord).filter_by(batch_id=batch_id)
    return query.all()

@check_session
def load_last_batch():
    batch = session.query(UploadBatch).order_by(desc(UploadBatch.id)).first()
    return batch

@check_session
def commit():
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
