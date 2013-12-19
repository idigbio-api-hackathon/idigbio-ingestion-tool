#!/usr/bin/env python
#
# Copyright (c) 2013 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module implements the data model for the service.
"""
from sqlalchemy import (create_engine, Column, Integer, String, DateTime,
                        Boolean, types)
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql.expression import desc
import logging, hashlib, argparse, os, time, struct, re
import pyexiv2
from datetime import datetime
import types as pytypes
from dataingestion.services import constants

THRESHOLD_TIME = 2 # sec

if os.name == 'posix':
  import pwd
elif os.name == 'nt':
  from dataingestion.services import win_api

__images_tablename__ = constants.IMAGES_TABLENAME
__batches_tablename__ = constants.BATCHES_TABLENAME

Base = declarative_base()

logger = logging.getLogger('iDigBioSvc.model')

def check_session(func):
  def wrapper(*args):
    if session is None:
      raise ValueError('DB session is None.')
    return func(*args)
  return wrapper


class ModelException(Exception):
  def __init__(self, msg, reason=''):
    Exception.__init__(self, msg)
    self.reason = reason


class UploadBatch(Base):
  """
  Represents a batch which is the operation executed when the user clicks the 
  "Upload" button.
  
  .. note:: When a batch fails and is resumed, the same batch record and 
     recordset id are reused.
  """
  __tablename__ = __batches_tablename__
  id = Column(Integer, primary_key=True)
  """The path for the batch upload."""
  CSVfilePath = Column(String)
  """Log in information."""
  iDigbioProvidedByGUID = Column(String)
  """The license key."""
  RightsLicense = Column(String)
  RightsLicenseStatementUrl = Column(String)
  RightsLicenseLogoUrl = Column(String)
  """The GUID user provided for the record set."""
  RecordSetGUID = Column(String)
  """Return from server."""
  RecordSetUUID = Column(String)
  """The local time at which the batch task starts."""
  start_time = Column(DateTime)
  """The local time that the batch upload finishes. None if not successful."""
  finish_time = Column(DateTime)
  """The following fields are optional."""
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
  
  def __init__(self, path, accountID, license, licenseStatementUrl, licenseLogoUrl,
    rs_guid, rs_uuid, s_time, md5, kw, proID, pubID, fs, fp):
    self.CSVfilePath = path
    self.iDigbioProvidedByGUID = accountID
    self.RightsLicense = license
    self.RightsLicenseStatementUrl = licenseStatementUrl
    self.RightsLicenseLogoUrl = licenseLogoUrl
    self.RecordSetGUID = rs_guid
    self.RecordSetUUID = rs_uuid
    self.start_time = s_time
    self.AllMD5 = md5
    self.MediaContentKeyword = kw
    self.iDigbioProviderGUID = proID
    self.iDigbioPublisherGUID = pubID
    self.FundingSource = fs
    self.FundingPurpose = fp
    self.RecordCount = 0
    self.SkipCount = 0
    self.FailCount = 0
    self.ErrorCode = None
    self.finish_time = None


class ImageRecord(Base):
  __tablename__ = __images_tablename__
  '''
  Note that "None" should not be used in DB because when the fields are returned
  to the Bootstrap UI as a list, the "None" element is ignored by Bootstrap,
  which leads to a mistake in list element indexes or list size.
  '''

  id = Column(Integer, primary_key=True)
  """
  Path does not have to be unique as there can be multiple 
  unrelated */USBVolumne1/DCIM/Image1.JPG*s.
  """
  OriginalFileName = Column(String)
  """
  MediaGUID (providerid) is unique for each media record within the record set.
  """
  MediaGUID = Column(String)
  """The UUID of the specimen for this image."""
  SpecimenRecordUUID = Column(String)
  """Indicates if there is a fatal error in the processing."""
  Error = Column(String)
  """Indicates if there are warnings in the processing."""
  Warnings = Column(String)
  """The UUID of the *media record* for this image."""
  MediaRecordUUID = Column(String)
  """The UUID of the *media AP* for this image."""
  MediaAPUUID = Column(String)
  """MadiaAP record in JSON String."""
  MediaAPContent = Column(types.BLOB)
  """
  The UTC time measured by the local machine. 
  None if the image is not uploaded.
  """
  UploadTime = Column(String)
  """The URL of the Media after posting the image."""
  MediaURL = Column(String)
  """MadiaRecord record in JSON String."""
  MediaRecordContent = Column(types.BLOB)
  """
  Technical type (format) of digital multimedia object. 
  When using the image ingestion appliance, this is automatically filled based
  on the extension of the filename.
  """
  MimeType = Column(String)
  """
  Size in bytes of the multimedia resource accessible through the MediaUrl. 
  Derived from the object when using the ingestion appliance.
  """
  MediaSizeInBytes = Column(String)
  """
  Date and time when the record was originally created on the provider data
  management system.
  """
  ProviderCreatedTimeStamp = Column(String)
  """File owner"""
  ProviderCreatedByGUID = Column(String)
  """
  Blob of text containing the EXIF metadata from the media.
  Derived from the object when using the ingestion appliance.
  """
  MediaEXIF = Column(types.BLOB)
  """All the annotations to the image by the user."""
  Annotations = Column(types.BLOB)
  """Returned by server at post_mediarecord."""
  etag = Column(String)
  """Checksum of the media object accessible via MediaUrl, using MD5."""
  MediaMD5 = Column(String)
  """Hash got from "record set uuid + CSV record line + media file hash"."""
  AllMD5 = Column(String, index=True, unique=True)
  """This image belongs to a specific batch."""
  BatchID = Column(Integer)

  def __init__(self, path, mediaguid, sruuid, error, warnings, mimetype,
               msize, ctime, fowner, exif, annotations, mmd5, amd5, batch):
    self.OriginalFileName = path
    self.MediaGUID = mediaguid
    self.SpecimenRecordUUID = sruuid
    self.Error = error
    self.Warnings = warnings
    self.MimeType = mimetype
    self.MediaSizeInBytes = msize
    self.ProviderCreatedTimeStamp = ctime
    self.ProviderCreatedByGUID = fowner
    self.MediaEXIF = exif
    self.Annotations = annotations
    self.MediaMD5 = mmd5
    self.AllMD5 = amd5
    self.BatchID = batch.id


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
  print "DB Connection: %s" % db_conn

def md5_file(f, block_size=2 ** 20):
  md5 = hashlib.md5()
  while True:
    data = f.read(block_size)
    if not data:
      break
    md5.update(data)
  return md5

def generate_record(csvrow, headerline, rs_uuid):
  logger.debug('Generating image record ...')
  
  mediapath = ""
  mediaguid = ""
  sruuid = ""
  error = ""
  warnings = ""
  mimetype = ""
  msize = ""
  ctime = ""
  fowner = ""
  exif = ""
  annotations_dict = {}
  mmd5 = ""
  amd5 = ""

  index = 0
  for index, elem in enumerate(headerline):
    if elem == "idigbio:OriginalFileName":
      mediapath = csvrow[index]
    elif elem == "idigbio:MediaGUID":
      mediaguid = csvrow[index]
    elif elem == "idigbio:SpecimenRecordUUID":
      sruuid = csvrow[index].replace(" ", "")
    else:
      annotations_dict[elem] = csvrow[index]

  recordmd5 = hashlib.md5()
  recordmd5.update(rs_uuid)
  recordmd5.update(mediapath)
  recordmd5.update(mediaguid)
  recordmd5.update(sruuid)

  exifinfo = None
  filemd5 = hashlib.md5()

  if not re.compile(constants.ALLOWED_FILES, re.IGNORECASE).match(mediapath):
    error = "File type unsupported."
  else:
    try:
      mimetype = constants.EXTENSION_MEDIA_TYPES[
          os.path.splitext(mediapath)[1].lower()]
    except os.error:
      logger.error("os path splitext error: " + mediapath)

    try:
      with open(mediapath, 'rb') as f:
        filemd5 = md5_file(f)
    except IOError as err:
      logger.error("File " + mediapath + " open error.")
      error = "File not found."

  if error: # File not exist, cannot go further. Just return.
    logger.debug('Generating image record done with error.')
    return (mediapath, mediaguid, sruuid, error, warnings, mimetype,
        msize, ctime, fowner, exif, str(annotations_dict), filemd5.hexdigest(),
        recordmd5.hexdigest())

  recordmd5.update(filemd5.hexdigest())

  try:
    msize = os.path.getsize(mediapath)
  except os.error:
    logger.error("os path getsize error: " + mediapath)
    warnings += "[File getsize error.]"

  ctime = time.ctime(os.path.getmtime(mediapath))

  if os.name == 'posix':
    fowner = pwd.getpwuid(os.stat(mediapath).st_uid)[0]
  elif os.name == 'nt':
    try:
      fowner = win_api.get_file_owner(mediapath)
    except Exception as e:
      logger.debug("WIN API error: %s" % e)
      traceback.print_exc()
      warnings += "Windows NT get file owner error."
  else:
    logger.error("Operating system not supported:" + os.name)
    warnings += "[OS not supported when getting file owner.]"

  try:
    exifinfo = pyexiv2.ImageMetadata(mediapath)
    exifinfo.read()
    if not exifinfo:
      exif = ""
      warnings += "[Cannot extract EXIF information.]"
    else:
      exif_dict = {}
      for exif_key in exifinfo.keys():
        try:
          if type(exifinfo[exif_key].value) in (
              pytypes.IntType, pytypes.LongType, pytypes.FloatType):
            exif_dict[exif_key] = exifinfo[exif_key].value
          elif exifinfo[exif_key].type in ("Flash"):
            exif_dict[exif_key] = exifinfo[exif_key].value
          else:
            exif_dict[exif_key] = str(exifinfo[exif_key].value)
        except: # There are some fields that cannot be extracted, just continue.
          continue
      exif = str(exif_dict)
  except IOError as err:
    warnings += "[Cannot extract EXIF information.]"

  logger.debug('Generating image record done.')
  return (mediapath, mediaguid, sruuid, error, warnings, mimetype, msize,
          ctime, fowner, exif, str(annotations_dict), filemd5.hexdigest(),
          recordmd5.hexdigest())

@check_session
def add_image(batch, csvrow, headerline):
  """
  Parameters:
    batch: The UploadBatch instance this image belongs to.
    csvrow: A list of values of the current csvrow.
    headerline: The header line of the csv file.
    rs_uuid: The UUID of the record set.
  Return the image or None is the image should not be uploaded.
  :rtype: ImageRecord or None.
  Note: Image identity is not determined by path but rather by its MD5.
  """
  (mediapath, mediaguid, sruuid, error, warnings, mimetype, msize, ctime,
      fowner, exif, annotations, mmd5, amd5) = generate_record(
          csvrow, headerline, batch.RecordSetUUID)

  try:
    record = session.query(ImageRecord).filter_by(AllMD5=amd5).first()
  except Exception as e:
    raise ModelException("Error occur during SQLITE access e:{0}".format(e))
  if record is None: # New record. Add the record.
    record = ImageRecord(mediapath, mediaguid, sruuid, error, warnings,
                         mimetype, msize, ctime, fowner, exif, annotations,
                         mmd5, amd5, batch)
    try:
      session.add(record)
    except Exception as e:
      raise ModelException("Error occur during SQLITE add e:{0}".format(e))
    return record
  elif record.UploadTime: # Found the duplicate record, already uploaded.
    return None
  else: # Found the duplicate record, but not uploaded or file not found.
    record.BatchID = batch.id
    return record

@check_session
def add_batch(path, accountID, license, licenseStatementUrl, licenseLogoUrl,
              recordset_guid, recordset_uuid, keyword, proID, pubID,
              fundingSource, fundingPurpose):
  '''
  Add a batch to the database.
  Returns: An UploadBatch instance created by the information.
  Throws ModelException:
    1. If path, accountID, license, licenseLogoUrl, recordset_guid or
       recordset_uuid are not all provided.
    2. If the provided CSV file path is not to a valid file.
  '''
  if (not path or not accountID or not license or not licenseLogoUrl or
      not recordset_guid or not recordset_uuid):
    raise ModelException("At lease one required field is not provided.")

  start_time = datetime.now()
  try:
    with open(path, 'rb') as f:
      md5value = md5_file(f)
  except:
    raise ModelException("CSV File %s is not a valid file." %path)
  md5value.update(accountID)
  md5value.update(license)
  md5value.update(recordset_guid)
  md5value.update(recordset_uuid)

  if keyword is None:
    keyword = ""
  if proID is None:
    proID = ""
  if pubID is None:
    pubID = ""
  if fundingSource is None:
    fundingSource = ""
  if fundingPurpose is None:
    fundingPurpose = ""

  md5value.update(keyword)
  md5value.update(proID)
  md5value.update(pubID)
  md5value.update(fundingSource)
  md5value.update(fundingPurpose)

  # Always add new record.
  newrecord = UploadBatch(path, accountID, license, licenseStatementUrl,
      licenseLogoUrl, recordset_guid, recordset_uuid, start_time,
      md5value.hexdigest(), keyword, proID, pubID, fundingSource,
      fundingPurpose)
  session.add(newrecord)
  return newrecord

@check_session
def get_batch_details(batch_id):
  '''Gets all the image records for a batch with batch_id.'''
  batch_id = int(batch_id)
  
  query = session.query(
      ImageRecord.OriginalFileName, ImageRecord.MediaGUID,
      ImageRecord.SpecimenRecordUUID, ImageRecord.Error,
      ImageRecord.Warnings, ImageRecord.MediaRecordUUID,
      ImageRecord.MediaAPUUID, ImageRecord.UploadTime, ImageRecord.MediaURL,
      ImageRecord.MimeType, ImageRecord.MediaSizeInBytes,
      ImageRecord.ProviderCreatedTimeStamp, ImageRecord.ProviderCreatedByGUID,
      ImageRecord.MediaEXIF, ImageRecord.Annotations, ImageRecord.etag,
      ImageRecord.MediaMD5, UploadBatch.CSVfilePath,
      UploadBatch.iDigbioProvidedByGUID, UploadBatch.RightsLicense,
      UploadBatch.RightsLicenseStatementUrl, UploadBatch.RightsLicenseLogoUrl,
      UploadBatch.RecordSetGUID, UploadBatch.RecordSetUUID,
      UploadBatch.MediaContentKeyword, UploadBatch.iDigbioProviderGUID,
      UploadBatch.iDigbioPublisherGUID, UploadBatch.FundingSource,
      UploadBatch.FundingPurpose, ImageRecord.BatchID
    ).filter(ImageRecord.BatchID == batch_id).filter(UploadBatch.id == batch_id
    ).order_by(ImageRecord.id) # 29 elements.
  
  logger.debug("Image record count: " + str(query.count()))

  return query.all()


@check_session
def get_all_batches():
  """
  Get all the batches in the batch table.
  Return: A list of all batches, each batch is a list of all fields.
  """

  query = session.query(
    UploadBatch.id, UploadBatch.CSVfilePath, UploadBatch.iDigbioProvidedByGUID,
    UploadBatch.RightsLicense, UploadBatch.RightsLicenseStatementUrl, 
    UploadBatch.RightsLicenseLogoUrl, UploadBatch.RecordSetGUID,
    UploadBatch.RecordSetUUID, UploadBatch.start_time, UploadBatch.finish_time,
    UploadBatch.MediaContentKeyword, UploadBatch.iDigbioProviderGUID,
    UploadBatch.iDigbioPublisherGUID, UploadBatch.FundingSource,
    UploadBatch.FundingPurpose, UploadBatch.RecordCount, UploadBatch.FailCount, 
    UploadBatch.SkipCount
    ).order_by(UploadBatch.id) # 18 elements
  
  ret = []
  for elem in query:
    newelem = []
    index = 0
    for origitem in elem:
      item = str(origitem)
      if index == 8:
        item = item[0:item.index('.')]
      newelem.append(str(item))
      index = index + 1
    ret.append(newelem)
  return ret

@check_session
def get_last_batch_info():
  """
  Returns info about the last batch.
  Returns:
    A dictionary of simple information about last batch. 
  """
  batch = session.query(UploadBatch).order_by(desc(UploadBatch.id)).first()
  if batch:
    starttime = str(batch.start_time)
    starttime = starttime[0:starttime.index('.')]
    retdict = {'Empty': False, 'path': batch.CSVfilePath,
               'start_time': starttime, 'ErrorCode': batch.ErrorCode}
    if batch.finish_time is None:
      retdict['finished'] = False
    else:
      retdict['finished'] = True
    dt = datetime.now() - batch.start_time
    if dt.seconds > THRESHOLD_TIME:
      # TODO: Avoid this trick
      # This is a trick, because network failure does not write to db.
      # Then we think the last record you get must be "old enough".
      # In contrast, the CSV file failure writes to db.
      # The the last record you get is just written a second ago.
      retdict['ErrorCode'] = 'Network Connection Error.'
    return retdict
  else:
    # TODO: Avoid this trick
    # If there's no record before, it is possible a network connection failure.
    retdict = {'Empty': True, 'ErrorCode': 'Network Connection Error.'}
    return retdict

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
