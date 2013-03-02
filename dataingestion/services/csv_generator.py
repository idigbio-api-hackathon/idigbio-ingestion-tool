#!/usr/bin/env python
#
# Copyright (c) 2012 Liu, Yonggang <myidpt@gmail.com>, University of Florida
#
# This software may be used and distributed according to the terms of the
# MIT license: http://www.opensource.org/licenses/mit-license.php

import re, os, logging, csv, hashlib
from os.path import isdir, join, dirname, split, exists
from dataingestion.services import user_config, constants
from dataingestion.services.ingestion_manager import IngestServiceException

logger = logging.getLogger('iDigBioSvc.csv_generator')


def get_files(imagepath):
	allowed_files = re.compile(constants.ALLOWED_FILES, re.IGNORECASE)
	filenameset = []
	
	if isdir(imagepath): # This is a dir.
		
		file_count = 0
		for dirpath, dirnames, filenames in os.walk(imagepath):
			for file_name in filenames:
				file_count = file_count + 1
				if file_count > constants.G_FILE_NUMBER_LIMIT:
					logger.error("File number is higher than the limit: " 
						+ str(constants.G_FILE_NUMBER_LIMIT))
					raise IngestServiceException("File number is higher than the limit: " 
						+ str(constants.G_FILE_NUMBER_LIMIT))
				
				if not allowed_files.match(file_name):
					continue
				subpath = join(dirpath, file_name)
				filenameset.append(subpath)

	
	else: # This is a single file.
		if allowed_files.match(imagepath):
			filenameset.append(imagepath)
	return filenameset

def get_mediaguids(guid_syntax, guid_prefix, filenameset, commonvalue):
	guidset = []
	if guid_syntax is None or guid_syntax == "":
		logger.error("GUID Syntax is empty.")
		raise IngestServiceException("GUID Syntax is empty.")
	if guid_syntax == "hash":
		for index in range(len(filenameset)):
			md5value = hashlib.md5()
			md5value.update(str(filenameset[index]))
			md5value.update(str(commonvalue))
			guidset.append(md5value.hexdigest())
	elif guid_syntax == "fullpath" or guid_syntax == "filename":
		for index in range(len(filenameset)):
			if guid_syntax == "filename":
				guid_postfix = split(filenameset[index])[1]
			else:
				guid_postfix = filenameset[index]
			guidset.append(guid_prefix + guid_postfix)
	else:
		logger.error("Error: guid_syntax is not defined: " + guid_syntax)
		raise IngestServiceException("GUID Syntax not defined: " + guid_syntax)
	return guidset

def generate_csv():
	
	imagedir = user_config.get_user_config(user_config.G_IMAGE_DIR)
	targetfile = user_config.get_user_config(user_config.G_SAVE_PATH)

	# Find all the media files.
	if not exists(imagedir):
		logger.error("IngestServiceException: " + imagedir + " is not a valid path.")
		raise IngestServiceException(imagedir + " is not a valid path.")
	
	filenameset = get_files(imagedir)
	if not filenameset:
		logger.error("IngestServiceException: No valid media file is in the path.")
		raise IngestServiceException("No valid media file is in the path.")

	# Find the headerline and commonvalues.
	headerline = ["idigbio:OriginalFileName", "idigbio:MediaGUID"]
	commonvalue = []

	description = user_config.get_user_config(user_config.G_DESCRIPTION)
	if description is not None and description != "":
		headerline.append("idigbio:Description")
		commonvalue.append(description)
	
	language_code = user_config.get_user_config(user_config.G_LANGUAGE_CODE)
	if language_code is not None and language_code != "":
		headerline.append("idigbio:LanguageCode")
		commonvalue.append(language_code)
	
	title = user_config.get_user_config(user_config.G_TITLE)
	if title is not None and title != "":
		headerline.append("idigbio:Title")
		commonvalue.append(title)
	
	digi_device = user_config.get_user_config(user_config.G_DIGI_DEVICE)
	if digi_device is not None and digi_device != "":
		headerline.append("idigbio:DigitalizationDevice")
		commonvalue.append(digi_device)

	pix_resolution = user_config.get_user_config(user_config.G_PIX_RESOLUTION)
	if pix_resolution is not None and pix_resolution != "":
		headerline.append("idigbio:NominalPixelResolution")
		commonvalue.append(pix_resolution)

	magnification = user_config.get_user_config(user_config.G_MAGNIFICATION)
	if magnification is not None and magnification != "":
		headerline.append("idigbio:Magnification")
		commonvalue.append(magnification)

	ocr_output = user_config.get_user_config(user_config.G_OCR_OUTPUT)
	if ocr_output is not None and ocr_output != "":
		headerline.append("idigbio:OcrOutput")
		commonvalue.append(ocr_output)

	ocr_tech = user_config.get_user_config(user_config.G_OCR_TECH)
	if ocr_tech is not None and ocr_tech != "":
		headerline.append("idigbio:OcrTechnology")
		commonvalue.append(ocr_tech)

	info_withheld = user_config.get_user_config(user_config.G_INFO_WITHHELD)
	if info_withheld is not None and info_withheld != "":
		headerline.append("idigbio:InformationWithheld")
		commonvalue.append(info_withheld)

	col_obj_guid = user_config.get_user_config(user_config.G_COLLECTION_OBJ_GUID)
	if col_obj_guid is not None and col_obj_guid != "":
		headerline.append("idigbio:CollectionObjectGUID")
		commonvalue.append(col_obj_guid)

	# Find the media GUIDs.
	guid_syntax = user_config.get_user_config(user_config.G_GUID_SYNTAX)
	guid_prefix = user_config.get_user_config(user_config.G_GUID_PREFIX)

	guidset = get_mediaguids(guid_syntax, guid_prefix, filenameset, commonvalue)
	#print(guidset)

	# Form the output stream
	outputstream = []
	index = 0
	for item in filenameset:
		tmp = []
		tmp.append(item)
		tmp.append(guidset[index])
		outputstream.append(tmp + commonvalue)
		index = index + 1
		#print(outputstream)

	# Write the CSV file.
	try:
		if targetfile is None or targetfile == "":
			if isdir(imagedir):
				targetfile = join(imagedir, constants.G_DEFAULT_CSV_OUTPUT_NAME)
			else:
				imagedir = dirname(imagedir)
				targetfile = join(imagedir, user_config.G_DEFAULT_CSV_OUTPUT_NAME)
			logger.debug("targetfile=" + targetfile)

		with open(targetfile, 'wb') as csvfile:
			csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			csvwriter.writerow(headerline)
			csvwriter.writerows(outputstream)
	except IOError as ex:
		raise IngestServiceException("Cannot write to output file: " + targetfile)
	return targetfile