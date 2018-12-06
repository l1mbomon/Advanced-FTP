############################################################################################################
#	here I shall create folders in the root test directory passed as an input.
#	then create files in it
#	randomly edit the files in it
#	explore corner cases
############################################################################################################
import sys
import re
import os
import random
import time

def createfolders(testdir, maxdepth):
	numsubfolders = random.randint(1,5)
	for subfol in range(numsubfolders):
		path = "/"+testdir+"/"+"folder"+str(subfol)
		if not os.path.exists(path):
			os.mkdir(path, 0755)
	#	goto = "cd "+path
	#	os.system(goto)
		numsub_folders = random.randint(0,int(maxdepth))
		recurse_create_sub(numsub_folders, path)

		numfiles = random.randint(0,3)
		for subfile in range(numfiles):
			print "trying to create subfiles"
			f = open(testdir+"/"+"folder"+str(subfol)+"/"+str(subfile)+".txt", "w+")
			lines = random.randint(0, 31)
			for i in range(lines): #number of lines I want to write into the file
				f.write("this is line %d\n" %(i+1))
			f.close
	
	#done creating files with random data.
					
def recurse_create_sub(depth, presentfolder):
	if not depth:
		return
	path = presentfolder+"/sub"+str(depth)
	print presentfolder
	print depth
	print path
	if not os.path.exists(path):
		os.mkdir(path, 0755)
	create_random_num_files(path)
	recurse_create_sub(depth-1, path)


def create_random_num_files(path):
		numfiles = random.randint(0,3)
		for subfile in range(numfiles):
			print "trying to create subfiles"
			f = open(path+"/"+str(subfile)+".txt", "w+")
			lines = random.randint(0, 31)
			for i in range(lines): #number of lines I want to write into the file
				f.write("this is line %d\n" %(i+1))
			f.close


#start making changes to existing files after creating!!!!!!!!!!!!!

def makechanges(topfolder):
	files = folders = 0
	string = {}
	dirs = []
	for dirpath, dirnames, filenames in os.walk(topfolder):
	#	files += len(filenames)
	#	folders += len(dirnames)
		# dirs += dirnames
		# print dirpath
		foldertoedit = random.randint(0, len(dirnames))
		if not foldertoedit:
			continue
		else:
			filetoedit = random.randint(0, len(filenames))
			if not filetoedit:
				continue
			else:
				#f = open(topfolder+"/"+str(filenames[filetoedit]), "a+")
	#			print os.path.join(dirpath, filenames[filetoedit-1])
				f = open(os.path.join(dirpath, filenames[filetoedit-1]), "r+")
				filecontent = f.readlines()
				# print len(filecontent)
				f.seek(0)
			#	print filecontent
				print "Length of file content {}".format(len(filecontent))
				if len(filecontent) != 0:
					linetoedit = random.randint(0, len(filecontent))
					filecontent[linetoedit-1] = filecontent[linetoedit-1]+" edited "
				else:
					filecontent = ["edited"]
				for lines in filecontent:
					f.write(lines)
					print lines
					#string = string + lines
				#f.write(string)
				f.close()
				print "edited the file"
				print dirpath+"/"+filenames[filetoedit-1]
				break

			
def main():
	if not sys.argv[1:]:
		print "usage: python auto.py <root_folder> <max depth of folder hierarchy> <time between edits>"
		sys.exit(1)
	time.sleep(15)
	createfolders(sys.argv[1], sys.argv[2])
	
	while True:
		time.sleep(float(sys.argv[3]))
		makechanges(sys.argv[1])


if __name__ == '__main__':
	main()

	
