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

def gen_csv(dic):

	# Find all the media files.
	imagedir = ""
	if dic.has_key(user_config.G_IMAGE_DIR):
		# To make special notations like '\' working.
		imagedir = dic[user_config.G_IMAGE_DIR].encode('string-escape')
	if not exists(imagedir):
		logger.error("IngestServiceException: " + imagedir + " is not a valid path.")
		raise IngestServiceException("\"" + imagedir + "\" is not a valid path.")
	filenameset = get_files(imagedir)
	if not filenameset:
		logger.error("IngestServiceException: No valid media file is in the path.")
		raise IngestServiceException("No valid media file is in the path.")
	
	# Find the headerline and commonvalues.
	headerline = ["idigbio:OriginalFileName", "idigbio:MediaGUID"]
	commonvalue = []

	# description
	if dic.has_key(user_config.G_DESCRIPTION) and dic[user_config.G_DESCRIPTION] != '':
		commonvalue.append(dic[user_config.G_DESCRIPTION])
		headerline.append("idigbio:Description")

	# language code
	if dic.has_key(user_config.G_LANGUAGE_CODE) and dic[user_config.G_LANGUAGE_CODE] != '':
		commonvalue.append(dic[user_config.G_LANGUAGE_CODE])
		headerline.append("idigbio:LanguageCode")

	# title
	if dic.has_key(user_config.G_TITLE) and dic[user_config.G_TITLE] != '':
		commonvalue.append(dic[user_config.G_TITLE])
		headerline.append("idigbio:Title")
	
	# digitalization_device
	if dic.has_key(user_config.G_DIGI_DEVICE) and dic[user_config.G_DIGI_DEVICE] != '':
		commonvalue.append(dic[user_config.G_DIGI_DEVICE])
		headerline.append("idigbio:DigitalizationDevice")

	# pixel resolution
	if dic.has_key(user_config.G_PIX_RESOLUTION) and dic[user_config.G_PIX_RESOLUTION] != '':
		commonvalue.append(dic[user_config.G_PIX_RESOLUTION])
		headerline.append("idigbio:NominalPixelResolution")

	# magnification
	if dic.has_key(user_config.G_MAGNIFICATION) and dic[user_config.G_MAGNIFICATION] != '':
		commonvalue.append(dic[user_config.G_MAGNIFICATION])
		headerline.append("idigbio:Magnification")

	# OCR output
	if dic.has_key(user_config.G_OCR_OUTPUT) and dic[user_config.G_OCR_OUTPUT] != '':
		commonvalue.append(dic[user_config.G_OCR_OUTPUT])
		headerline.append("idigbio:OcrOutput")

	# OCR technology
	if dic.has_key(user_config.G_OCR_TECH) and dic[user_config.G_OCR_TECH] != '':
		commonvalue.append(dic[user_config.G_OCR_TECH])
		headerline.append("idigbio:OcrTechnology")

	# information withheld
	if dic.has_key(user_config.G_INFO_WITHHELD) and dic[user_config.G_INFO_WITHHELD] != '':
		commonvalue.append(dic[user_config.G_INFO_WITHHELD])
		headerline.append("idigbio:InformationWithheld")

	# Collection Object GUID
	if dic.has_key(user_config.G_COLLECTION_OBJ_GUID) and dic[user_config.G_COLLECTION_OBJ_GUID] != '':
		commonvalue.append(dic[user_config.G_COLLECTION_OBJ_GUID])
		headerline.append("idigbio:CollectionObjectGUID")

	# Find the media GUIDs.
	if dic.has_key(user_config.G_GUID_SYNTAX):
		guid_syntax = dic[user_config.G_GUID_SYNTAX]
	else:
		raise IngestServiceException("GUID syntax is missing.")

	if dic.has_key(user_config.G_GUID_PREFIX):
		guid_prefix = dic[user_config.G_GUID_PREFIX]

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
	targetfile = ""
	if dic.has_key(user_config.G_SAVE_PATH):
		targetfile = dic[user_config.G_SAVE_PATH].encode('string-escape')
	try:
		if targetfile == "":
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