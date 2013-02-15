import random, os, sys, re

VERSION_LIMIT = (3,0)
version = sys.version_info

if version < VERSION_LIMIT:
	import urllib2 # for Python 2.7, etc.
else:
	import urllib.request # for Python 3.3, etc.


acceptable_fields = ["idigbio:OriginalFileName", "idigbio:MediaGUID", "idigbio:Description", "idigbio:LanguageCode", 
    "idigbio:Title", "idigbio:DigitalizationDevice", "idigbio:NominalPixelResolution", "idigbio:Magnification", 
    "idigbio:OcrOutput", "idigbio:OcrTechnology", "idigbio:InformationWithheld"]

field_values = ["", "", "Scanned herbarium sheet with secimen collected West of Plant City 4 miles from Mango \
	ct., on Hwy 92.", "en", "Ilex glabra from FSU", "Canon Supershot 2000", "128mm", "4x", "This is OCR output.", "Tesseract version \
	3.01 on Windows, latin character set", "location information not given for endangered species, contact my@email"]

acceptable_fields_print = ["idigbio:OriginalFileName (Required)", "idigbio:MediaGUID (Required)", "idigbio:Description", "idigbio:LanguageCode", 
    "idigbio:Title", "idigbio:DigitalizationDevice", "idigbio:NominalPixelResolution", "idigbio:Magnification", 
    "idigbio:OcrOutput", "idigbio:OcrTechnology", "idigbio:InformationWithheld"]

TIMEOUT=5
MAX_NUM = 1000000

num_records = 2
file_url = "http://www.acis.ufl.edu/~yonggang/idigbio/dataset/"
file_list_name = "file_list"
csv_name = "test_input.csv"
url_guid = "www.fakeurl.edu/abc/def/image"

def retrieveURL(url):
	if version < VERSION_LIMIT:
		data = urllib2.urlopen(url, timeout=TIMEOUT).read() # for Python 2.7, etc.
	else:
		data = urllib.request.urlopen(url, timeout=TIMEOUT).read() # for Python 3.3, etc.
	return data

def writeFile(filename, line):
	if version < VERSION_LIMIT:
		filename.write(line)
	else:
		filename.write(bytes(line, 'UTF-8'))

def printAcceptableFields():
	print("Acceptable fields include the following elements, please list them exactly as shown:")
	for elem in acceptable_fields_print:
		print("  " + elem)

def retrieveFileList(url):
	file_list = retrieveURL(url)
	dirfile = open("dirfile.txt", "wb")
	dirfile.write(file_list)
	dirfile.close()
	with open("dirfile.txt") as f:
		files = f.readlines()
	count = 0
	for file_elem in files:
		if file_elem == '':
			del files[count]
		else:
			if "\n" in files[count]:
				files[count] = files[count][:-1]
			count = count + 1
	print("Total files in list = " + str(count))
	return files

def retrieveMedia(file_name):
	url = file_url + file_name
	url = url.replace(' ', '%20')
	print("Retrieve file: " + str(url))
	mediadata = retrieveURL(url)
	index = file_name.rfind('/')
	file_name = file_name[index + 1:]
	mediafile = open(file_name, 'wb')
	mediafile.write(mediadata)
	mediafile.close()

inputlist = sys.argv

inputlist = inputlist[1:]
print("Field names: " + str(inputlist))

orderlist = []
for elem in inputlist:
	if elem in acceptable_fields:
		orderlist.append(acceptable_fields.index(elem))
	else:
		print("Error: field " + elem + " is not supported.")
		printAcceptableFields()
		exit()

if 0 not in orderlist:
	print("Error: idigbio:OriginalFileName field is not provided.")
	printAcceptableFields()
	exit()
if 1 not in orderlist:
	print("Error: idigbio:MediaGUID field is not provided.")
	printAcceptableFields()
	exit()

random.seed()

mediapath = os.getcwd() + str("/")

try:
	os.remove(csv_name)
except OSError as err:
	pass

url = file_url + file_list_name
print("File list URL: " + url)

files = retrieveFileList(url)

count = len(files)
if count < num_records:
	print("Total files in list is bigger than required number of files.")
	sys.exit()

start_position = int((count - num_records) * random.random())
end_position = start_position + num_records
print("Start position = " + str(start_position))
print("End position = " + str(end_position))

i = 0
csvfile = open(csv_name, "wb")
# Print the header line.
record = ""
for elem in orderlist:
	record += str("\"" + acceptable_fields[elem] + "\",")
record = record[:-1]
record += "\n"
writeFile(csvfile, record)

# Print the values line by line.
for file_elem in files:
	if i >= start_position and i < end_position:
		retrieveMedia(file_elem)
		index = file_elem.rfind('/')
		file_elem = file_elem[index + 1:]
		record = ""
		for elem in orderlist:
			if elem == 0:
				record += str("\"" + mediapath + file_elem + "\",")
			elif elem == 1:
				record += str("\"" + url_guid + str(int(MAX_NUM * random.random())) + "\",")
			else:
				record += str("\"" + field_values[elem] + "\",")
		record = record[:-1]
		record += "\n"
		writeFile(csvfile, record)
	i = i + 1
csvfile.close()
