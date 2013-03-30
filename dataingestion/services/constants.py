IMAGE_LICENSES = {
    "CC0": ["CC0", "(Public Domain)", "http://creativecommons.org/publicdomain/zero/1.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/publicdomain.png"],
    "CC BY": ["CC BY", "(Attribution)", "http://creativecommons.org/licenses/by/3.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by.png"],
    "CC BY-SA": ["CC BY-SA", "(Attribution-ShareAlike)", "http://creativecommons.org/licenses/by-sa/3.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by-sa.png"],
    "CC BY-NC": ["CC BY-NC", "(Attribution-Non-Commercial)", "http://creativecommons.org/licenses/by-nc/3.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by-nc.png"],
    "CC BY-NC-SA": ["CC BY-NC-SA", "(Attribution-NonCommercial-ShareAlike)", "http://creativecommons.org/licenses/by-nc-sa/3.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by-nc-sa.png"]
};

ALLOWED_FILES = '(.*?)\.(jpg|jpeg|tiff|tif)$'
'''
Regex of allowed files. Will be matched case-insensitively.
'''

EXTENSION_MEDIA_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "tif": "image/tiff",
}

CSV_TYPE = "csv_type"
DIR_TYPE = "dir_type"

INPUT_CSV_FIELDNAMES = [
	"idigbio:OriginalFileName", "idigbio:MediaGUID", "idigbio:Description", "idigbio:LanguageCode", 
    "idigbio:Title", "idigbio:DigitalizationDevice", "idigbio:NominalPixelResolution", "idigbio:Magnification", 
    "idigbio:OcrOutput", "idigbio:OcrTechnology", "idigbio:InformationWithheld", "idigbio:CollectionObjectGUID"
]

G_DEFAULT_CSV_OUTPUT_NAME = 'media_records.csv'
G_FILE_NUMBER_LIMIT = 10000
# Control the number of directrys traveling through, prevent the problem to be too large.

IMAGES_TABLENAME = 'imagesV8_5'
BATCHES_TABLENAME = 'batchesV8_5'