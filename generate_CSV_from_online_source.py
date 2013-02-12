import random, urllib2, os, sys, re

TIMEOUT=5
MAX_NUM = 1000000

num_records = 5
file_url = "http://www.acis.ufl.edu/~yonggang/idigbio/dataset/"
file_list_name = "file_list"
csv_name = "test_input.csv"

other_record_info = "\"Scanned herbarium sheet with secimen collected West of Plant City 4 miles from Mango Jct., on Hwy 92.\", \"en\", \"Ilex glabra from FSU\", \"Canon Supershot 2000\", \"128mm\", \"4x\", \"\", \"Tesseract version 3.01 on Windows, latin character set\", \"location information not given for endangered species, contact my@email\""
url_guid = "www.fakeurl.edu/abc/def/image"

random.seed()

mediapath = os.getcwd() + str("/")

try:
	os.remove(csv_name)
except OSError as err:
	pass

url = file_url + file_list_name
print "File list URL: " + url

file_list = urllib2.urlopen(url, timeout=TIMEOUT).read()

count = 0
files = re.split('\n', file_list)
for file_elem in files:
	if file_elem == '':
		del files[count]
	else:
		count = count + 1
print "Total files in list = " + str(count)

if count < num_records:
	print "Total files in list is bigger than required number of files."
	sys.exit()

start_position = int((count - num_records) * random.random())
end_position = start_position + num_records
print "Start position = " + str(start_position)
print "End position = " + str(end_position)

i = 0
csvfile = open(csv_name, "wb")
for file_elem in files:
	if i >= start_position and i < end_position:
		url = file_url + file_elem
		url = url.replace(' ', '%20')
		print "Retrieve file: " + str(url)
		mediadata = urllib2.urlopen(url, timeout=TIMEOUT).read()
		index = file_elem.rfind('/')
		file_elem = file_elem[index + 1:]
		mediafile = open(file_elem, 'wb')
		mediafile.write(mediadata)
		mediafile.close()
		record = ("\"" + mediapath + file_elem + "\", \"" + url_guid + 
			str(int(MAX_NUM * random.random())) + "\", " + other_record_info + "\n")
		csvfile.write(record)
	i = i + 1

