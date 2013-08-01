#!/usr/bin/env python

from PIL import Image
from PIL.ExifTags import TAGS

#from gi.repository import GExiv2
import pyexiv2


"""
exifinfo = Image.open("./VSC0001026.jpg")._getexif()


if (exifinfo is None):
    print "Fail to open"
else:
	metadata = {}
	for tag, value in exifinfo.items():
		decoded = TAGS.get(tag, tag)
		print("\t{0} \t {1} \t {2} \t {3}".format(tag, decoded, type(value), value)) #QHO
		metadata[decoded] = value
	mbuffer = str(metadata)
	print mbuffer
"""

metadata = pyexiv2.ImageMetadata("./VSC0001026.jpg")
metadata.read()
#print metadata.exif_keys
tag = metadata['Exif.Image.DateTime']
#print tag
#print tag.type
#print tag.value

for exif_key in metadata.keys():
	if metadata[exif_key].type not in ("Byte", "Undefined"): 
		print exif_key 
		#print metadata[exif_key].type
		#print metadata[exif_key].value 
	else:
		print exif_key 
		print metadata[exif_key].value 
		



