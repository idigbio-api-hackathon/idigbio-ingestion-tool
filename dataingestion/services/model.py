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

if os.name == 'posix':
    import pwd
elif os.name == 'nt':
    from dataingestion.services import win_api
from PIL import Image
from PIL.ExifTags import TAGS

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
    OriginalFileName = Column(String)
    '''
    Path does not have to be unique as there can be multiple 
    unrelated */USBVolumne1/DCIM/Image1.JPG*s.
    '''
    FileError = Column(String)
    '''
    Indicates if the given path is a valid file.
    '''
    MediaGUID = Column(String)
    '''
    MediaGUID (providerid) is unique for each media record within the record set.
    '''
    MediaRecordUUID = Column(String)
    '''
    The UUID of the *media record* for this image. 
    '''
    MediaAPUUID = Column(String)
    '''
    The UUID of the *media AP* for this image.
    '''
    AllMD5 = Column(String, index=True, unique=True)
    '''
    Hash got from "record set uuid + CSV record line + media file hash".
    '''
    Comments = Column(String)
    '''
    Any comments that is given by users.
    '''
    UploadTime = Column(String)
    '''
    The UTC time measured by the local machine. 
    None if the image is not uploaded.
    '''
    MediaURL = Column(String)

    MediaRecordContent = Column(types.BLOB)
    '''
    MadiaRecord record in JSON String
    '''
    MediaAPContent = Column(types.BLOB)
    '''
    MadiaAP record in JSON String
    '''
    Description = Column(String)
    '''
    http://purl.org/dc/terms/description
    '''
    LanguageCode = Column(String)
    '''
    http://purl.org/dc/terms/language
    '''
    Title = Column(String)
    '''
    http://purl.org/dc/terms/title
    '''
    DigitalizationDevice = Column(String)
    '''
    http://rs.tdwg.org/ac/terms/captureDevice
    '''
    NominalPixelResolution = Column(String)
    '''
    e.g., 128micrometer
    '''
    Magnification = Column(String)
    '''
    4x, 100x
    '''
    OcrOutput = Column(String)
    '''
    Output of the process of applying OCR to the multimedia object.
    '''
    OcrTechnology = Column(String)
    '''
    Tesseract version 3.01 on Windows, latin character set.
    '''
    InformationWithheld = Column(String)
    '''
    http://rs.tdwg.org/dwc/terms/informationWithheld
    '''
    CollectionObjectGUID = Column(String)
    '''
    Specimen ID.
    '''
    MediaMD5 = Column(String)
    '''
    Checksum of the media object accessible via MediaUrl, using MD5.
    '''
    MimeType = Column(String)
    '''
    Technical type (format) of digital multimedia object. 
    When using the image ingestion appliance, this is automatically filled based on the 
    extension of the filename.
    '''
    MediaSizeInBytes = Column(String)
    '''
    Size in bytes of the multimedia resource accessible through the MediaUrl. 
    Derived from the object when using the ingestion appliance.
    '''
    ProviderCreatedTimeStamp = Column(String)
    '''
    Date and time when the record was originally created on the provider data management system.
    '''
    providerCreatedByGUID = Column(String)
    '''
    File owner
    '''
    MediaMetadata = Column(types.BLOB)
    '''
    Blob of text containing metadata about the media (e.g., from EXIF, IPTC). 
    Derived from the object when using the ingestion appliance.
    '''
    etag = Column(String)
    '''
    Returned by server.
    '''

    # Changed because BatchID may be changed to map to other elements in batch table.
    BatchID = Column(Integer)
    #BatchID = Column(Integer, ForeignKey(__batches_tablename__+'.id', onupdate="cascade"))

    def __init__(self, path, pid, r_md5, error, batch, 
        desc, lang, title, digi, pix, mag, ocr_output, ocr_tech, info_withheld, col_obj_guid, 
        m_md5, mime_type, m_size, ctime, f_owner, metadata):
        self.OriginalFileName = path
        self.MediaGUID = pid
        self.AllMD5 = r_md5
        self.FileError = error
        self.BatchID = batch.id
        self.Description = desc
        self.LanguageCode = lang
        self.Title = title
        self.DigitalizationDevice = digi
        self.NominalPixelResolution = pix
        self.Magnification = mag
        self.OcrOutput = ocr_output
        self.ocrTechnology = ocr_tech
        self.InformationWithheld = info_withheld
        self.CollectionObjectGUID = col_obj_guid
        self.MediaMD5 = m_md5
        self.MimeType = mime_type
        self.MediaSizeInBytes = m_size
        self.ProviderCreatedTimeStamp = ctime
        self.providerCreatedByGUID = f_owner
        self.MediaMetadata = metadata

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
    # The following fields are optional.
    MediaContentKeyword = Column(String)
    iDigbioProviderGUID = Column(String)
    iDigbioPublisherGUID = Column(String)
    FundingSource = Column(String)
    FundingPurpose = Column(String)

    RecordCount = Column(Integer)
    SkipCount = Column(Integer)
    FailCount = Column(Integer)
    ErrorCode = Column(String)

    AllMD5 = Column(String) # The md5 of the CSV file + uuid.
    # images = relationship(ImageRecord, backref="batch") # All images associated with the batches in the table.
    
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
        self.AllMD5 = md5
        self.batchtype = btype
        self.MediaContentKeyword = kw
        self.iDigbioProviderGUID = proID
        self.iDigbioPublisherGUID = pubID
        self.FundingSource = fs
        self.FundingPurpose = fp

session = None

def setCSVFieldNames(headerline):
    orderlist = [] # The order of the input fields in constants.INPUT_CSV_FILENAMES.
#    logger.debug("The format of input CSV file:")
#    logger.debug(headerline)
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
    logger.debug('Generating image record ...')
    
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
    col_obj_guid = ""
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
        elif elem == 11:
            col_obj_guid = csvrow[index]
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
    recordmd5.update(col_obj_guid)

    name = ""
    exifinfo = None

    allowed_files = re.compile(constants.ALLOWED_FILES, re.IGNORECASE)
    if not allowed_files.match(mediapath): # This file is not allowed.
        file_error = "File type unsupported."
    else:
        try:
            name = os.path.splitext(mediapath)[1].split('.')
            extension = name[len(name)-1].lower()
            mime_type = constants.EXTENSION_MEDIA_TYPES[extension]
        except os.error:
            logger.error("os path splitext error: " + mediapath)

        try:
            with open(mediapath, 'rb') as f:
                filemd5 = md5_file(f)
        except IOError as err:
            logger.error("The file " + mediapath + " open error.")
            file_error = "File not found."

    if file_error == None:
        recordmd5.update(filemd5.hexdigest())
        
        try:
            media_size = os.path.getsize(mediapath)
        except os.error:
            logger.error("os path getsize error: " + mediapath)

        ctime = time.ctime(os.path.getmtime(mediapath))

        if os.name == 'posix':
            owner = pwd.getpwuid(os.stat(mediapath).st_uid)[0]
        elif os.name == 'nt':
            try:
                owner = win_api.get_file_owner(mediapath)
            except Exception as err:
                logger.debug("WIN API error: %s" % err)
                traceback.print_exc()
        else:
            logger.error("Operating system not supported:" + os.name)

        try:
            exifinfo = Image.open(mediapath)._getexif()

            if (exifinfo is None):
                logger.debug("File metadata is malformed: " + mediapath)
                mbuffer = ""
            else:
                metadata = {}
                logger.debug("\ttag \t\t\t decoded \t\t\t value") #QHO
                for tag, value in exifinfo.items():
                    decoded = TAGS.get(tag, tag)
                    logger.debug("\t{0} \t\t\t {1} \t\t\t {2}".format(tag, decoded, value)) #QHO
                    metadata[decoded] = value
                mbuffer = str(metadata)

        except IOError as err:
            logger.debug("File metadata is malformed: " + mediapath)

    logger.debug('Generating image record done.')
    return (mediapath,mediaproviderid,recordmd5.hexdigest(),file_error,desc,lang,title,digi,pix,
        mag,ocr_output,ocr_tech,info_withheld,col_obj_guid, filemd5.hexdigest(),mime_type,media_size,ctime, 
        owner,mbuffer)

# decorator
@check_session
def add_or_load_image(batch, csvrow, orderlist, rs_uuid, tasktype):
    '''
    Return the image or None is the image should not be uploaded.
    :rtype: ImageRecord or None.
    .. note:: Image identity is not determined by path but rather by its MD5.
    '''
    logger.debug("Updating image record ...")
    (mediapath,mediaproviderid,recordmd5,file_error,desc,lang,title,digi,pix,mag,ocr_output,ocr_tech,
        info_withheld,col_obj_guid,filemd5,mime_type,media_size,ctime,owner,
        metadata) = generate_record(csvrow, orderlist, rs_uuid)

    record = session.query(ImageRecord).filter_by(AllMD5=recordmd5).first()
    if record is None: # New record. Add the record.
        record = ImageRecord(mediapath, mediaproviderid, recordmd5, file_error, batch, 
            desc, lang, title, digi, pix, mag, ocr_output, ocr_tech, info_withheld, col_obj_guid, 
            filemd5, mime_type, media_size, ctime, owner, metadata)
        session.add(record)
        logger.debug("Updating ImageRecord done: New record.")
        #logger.debug('add_or_load_image: new record added')
        return record
    elif record.UploadTime: # Found the duplicate record, already uploaded.
        #record.BatchID = batch.id
        logger.debug("Updating ImageRecord done: Already uploaded and done.")
        return None
    else: # Found the duplicate record, but not uploaded or file not found.
        record.BatchID = batch.id
        logger.debug("Updating ImageRecord done: Record not fully finished.")
        return record

@check_session
def add_upload_batch(path, loginID, license, licenseStatementUrl, licenseLogoUrl, recordset_guid, 
    recordset_uuid, tasktype, keyword, proID, pubID, fundingSource, fundingPurpose):
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

@check_session
def get_imagerecords_by_batchid(batch_id):
    batch_id = int(batch_id)
    imagerecords = session.query(ImageRecord).filter_by(BatchID=batch_id)
    return imagerecords

@check_session
def count_batch_size(batch_id):
    batch_id = int(batch_id)
    query = session.query(UploadBatch).filter_by(id=batch_id).join(UploadBatch.images)
    return query.count()

@check_session
def get_batch_details(batch_id):
    batch_id = int(batch_id)
    
    query = session.query(
        ImageRecord.OriginalFileName, ImageRecord.FileError, ImageRecord.MediaGUID, 
        ImageRecord.MediaRecordUUID, ImageRecord.MediaAPUUID, ImageRecord.Comments, ImageRecord.UploadTime,
        ImageRecord.MediaURL, ImageRecord.Description, ImageRecord.LanguageCode, ImageRecord.Title,
        ImageRecord.DigitalizationDevice, ImageRecord.NominalPixelResolution, ImageRecord.Magnification,
        ImageRecord.OcrOutput, ImageRecord.OcrTechnology, ImageRecord.InformationWithheld, 
        ImageRecord.CollectionObjectGUID, ImageRecord.MediaMD5, ImageRecord.MimeType, 
        ImageRecord.MediaSizeInBytes, ImageRecord.ProviderCreatedTimeStamp, ImageRecord.providerCreatedByGUID,
        ImageRecord.etag, UploadBatch.RecordSetUUID, UploadBatch.iDigbioProvidedByGUID,
        UploadBatch.MediaContentKeyword, UploadBatch.FundingSource, UploadBatch.FundingPurpose,
        UploadBatch.iDigbioPublisherGUID, UploadBatch.RightsLicenseStatementUrl, 
        UploadBatch.RightsLicenseLogoUrl, UploadBatch.iDigbioProviderGUID, UploadBatch.RightsLicense, 
        UploadBatch.CSVfilePath, UploadBatch.RecordSetGUID, ImageRecord.BatchID
        ).filter(ImageRecord.BatchID == batch_id).filter(UploadBatch.id == batch_id
        ).order_by(ImageRecord.id) # 26 elements.
    
    logger.debug("Image record count: " + str(query.count()))
    #for item in query:
    #    for elem in item:
    #        logger.debug(elem)

    #query = session.query(ImageRecord).filter_by(BatchID=batch_id)
    return query.all()

def get_all_batches():
    logger.debug("get all the batches in the batch table.")
    
    query = session.query(
        UploadBatch.id, UploadBatch.CSVfilePath, UploadBatch.iDigbioProvidedByGUID,
        UploadBatch.RightsLicense, UploadBatch.RightsLicenseStatementUrl, 
        UploadBatch.RightsLicenseLogoUrl, UploadBatch.RecordSetGUID, UploadBatch.RecordSetUUID,
        UploadBatch.start_time, UploadBatch.finish_time, UploadBatch.MediaContentKeyword,
        UploadBatch.iDigbioProviderGUID, UploadBatch.iDigbioPublisherGUID, UploadBatch.FundingSource,
        UploadBatch.FundingPurpose, UploadBatch.RecordCount, UploadBatch.FailCount, 
        UploadBatch.SkipCount
        ).order_by(UploadBatch.id) # 18 elements
    
    logger.debug("Batch count: " + str(query.count()))
    logger.debug("get_all_batches done")
    ret = []
    for elem in query:
        newelem = []
        index = 0
        for origitem in elem:
            item = str(origitem)
            if index == 8:
                item = item[0:item.index('.')]
            #if index == 9:
            #    try:
            #        item = item[0:item.index('.')]
            #        item = "Successful"
            #    except ValueError as ex:
            #        item = "Failed"
            #if index == 15:
            #    if origitem is None:
            #        item = "0" # No record.
            newelem.append(str(item))
            index = index + 1
        ret.append(newelem)
    #print(ret)
    return ret

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
