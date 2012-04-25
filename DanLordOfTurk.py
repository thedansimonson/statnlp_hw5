"""
Dan Simonson's Library of Sweet Functions for Handling Mechanical Turk Data
*** SPECIAL EDITION FOR StatNLP HW5 ***

Est. 2012 01 24

I had a disparate, messy pile of functions and classes, blurred between
programming paradigms, for handling MechTurk data. I got tired of it one day
and said, "I shall write a library." This is that library. Here are the 
design principles I'm putting into it:
	+ Turk Data will be handled with dicts. None of this WordData class crap.
	+ Each question gets its own dict. No questions asked. 
	+ All properties, including what HIT it belongs to, are stored in the dict.
	+ Un-needed properties in a particular script are STRIPPED separately.

This is a first version. I'll probably realize working on this that these
are an awful idea. When I first jumped into this, though, I didn't have a plan.
Now I know what to plan for.

"""

from os import getcwd, listdir
from csv import reader

##############
# LOAD STUFF #
##############

#get all files in the current working directory that fit pattern
def getFilenames(pattern=lambda x: x[-3:] == "csv"):
	return filter(pattern, listdir(getcwd()))

#gives the user a prompt for a pattern for getFilenames()
def promptForFiles():
	print "Provide a load pattern."
	print "Example: '.csv' gives 'a.csv','b.csv', etc."
	loadPattern = raw_input("Specify load pattern: ")
	loadPatternF = lambda x: x[-len(loadPattern):] == loadPattern

	filenames = getFilenames(pattern=loadPatternF)
	return filenames
	

#loads a CSV from Amazon mechanical turk.
def loadTurkData(filenames):
	#empty case
	if not filenames:
		return []
	
	#general case
	inData = map(lambda x:x, reader(open(filenames[0],"r")))

	keyRow = inData[0]
	dataRows = inData[1:]
	
	#combines everything with its headers
	table = simpleTable(keyRow, dataRows)

	#save the filename in each q
	map(lambda x: x.update([("Input.filename", filenames[0])]) , table)
	
	#break question into its own dict
	table = reduce(lambda x,y: x+y, map(retokenizeTable, table))

	return table + loadTurkData(filenames[1:])


def simpleTable(indices, rowsOfListsOfData):
	return map(lambda x: dict(zip(indices, x)), rowsOfListsOfData)
	
#returns a table created in load table as a list of single inquiries
#tweaked specially for the turk format
#currently designed SOLELY for run 4
#needs a more general approach in the future

#changes for run 4
# + must flag pos/neg controls as such
# + remove incomplete hit controls
# + 

#
#If onlyAccepted = True and onlyComplete = True, return errorValue
def retokenizeTable(table, onlyAccepted = True, onlyComplete = True):
	numberOfInquiries = 2
	errorValue = []
	#names of things within the table that need to each ahve their own table
	uniqueNames = [
			lambda x: "annotator"+str(x),
			lambda x: "value"+str(x)
		]

	#grab all of the names unique to each inquiry
	allUniqueNames = reduce(lambda x,y: x+y, \
		map(lambda x: map(lambda n: n(x), uniqueNames), \
				range(1,numberOfInquiries+1)))
	
	#get the names of the indices that each inquiry will be bound with
	nonUniqueNames = filter(lambda x: x not in allUniqueNames,table)

	#all hail explosive growth!
	inquiries = []
	for each in range(1,numberOfInquiries+1):
		inquiry = []
		extractUniqueInfo = lambda x: (x(""), table[x(each)])
		extractPlainInfo = lambda x: (x, table[x])

		#get all of the entires unique to this inquiry
		inquiry += map(extractUniqueInfo, uniqueNames)

		#get all of the entries not unique to this inquiry
		inquiry += map(extractPlainInfo, nonUniqueNames)

		inquiries.append(dict(inquiry))

	return inquiries

# FREE TABLES
"""
Why free tables?

So far, I've been using dicts of dicts to store data. However, the realization
I had working on this library is that the best approach is a list of dicts, where 
each dict contains all the relevant values for a particular piece of data--ie, this
turker said THIS for THAT, and all this metadata comes with it.

Free tables aren't intended for turk data, though there may be a way to implement them.
Instead, they're used for tables of values. They could be used for even richer data
sets, but I won't get into that here. 

The dict of dicts approach is complicated and confusing. My head has spun so many times
trying to wrap my head around the data structure. It's really cumbersome to work with. 
Free tables, on the other hand, are manipulable in many ways, and can be easily used 
to produce a dict of dicts if it is desired (and sometimes, it is). You would use the
"indexBy" function in manipulating tables to do this. 
"""
#loads a table such that:
# table = [{row: ..., col: ..., value: ...},
#            {row: ..., ... } ]
# so instead of nested dictionaries, it's a list of dictionaries
# to access particular elements or sets of elements, use "filter"
#
# *Alias gives what the key names
# *Proc preprocesses a particular value before it is stored in the dict
#
def loadFreeTable(rawfile, defaultValue = 0, 
                    rowAlias = "row", colAlias = "col", valAlias = "value",
                    rowProc = lambda x: x, colProc = lambda x: x, valProc = lambda x: x):
    rawContent = rawfile.readlines()

    columnNames = rawContent[0].strip("\n").split(",")[1:]
    rows = map(lambda x: x.split(","), rawContent[1:])

    #load values in with appropriate labels
    table = []
    for row in rows:
        rowName = row[0]
        row = row[1:]
        for colName, value in zip(columnNames, row):
            try: valProc(value)
            except ValueError: value = defaultValue
            table.append({rowAlias: rowProc(rowName), 
                            colAlias: colProc(colName),
                            "value": valProc(value)})
    return table

#######################
# MANIPULATING TABLES #
#######################

#Watch the data stripper remove all your unwanted data.
def dataStripper(table, wantedData):
	pass

#merge two categories throughout the table
#intended for pivot tables
#UNTESTED
def mergeCategories(table, mergeList, newName="default", op=lambda x,y: x+y):
	newKey = newName
	for each in table:
		table[each][newKey] = reduce(op, map(lambda k: \
				table[each][k], mergeList))
		for key in mergeList: del table[each][key] #clean up old categories
	return table

#creates a dict of lists of dicts with the same value for the dict index key
#UNTESTED
def indexBy(key, table):
	indexedEntries = {}
	for each in table:
		keyValue = each[key]
		if keyValue in indexedEntries:
			indexedEntries[keyValue] += [each]
		else:
			indexedEntries[keyValue] = [each]
	return indexedEntries

#turn a list of dictionaries into a pivot table
# takes every dictionary, finds the value of colKey,
# then augments the rowKey value in that entry in the 
# new table.
#I could have just done this whole thing with indexBy? maybe?
def pivotize(rowKey, colKey, table):
	pivot = {}
	colsEncountered = []

	#tally values
	for each in table:
		row = each[rowKey]
		col = each[colKey]
		colsEncountered += [col]

		#has this token not been seen before?
		if row not in pivot:
			pivot[row] = {}
		
		#count a particular data item
		if col not in pivot[row]:
			pivot[row][col] = 1
		else:
			pivot[row][col] += 1
	
	#give zeros for all non-encountered values
	colsEncountered = set(colsEncountered)
	for each in pivot:
		for more in colsEncountered:
			if more not in pivot[each]:
				pivot[each][more] = 0
	return pivot
	

#for a free table,
#get all possible values for key
#equivalent to typecasting a dict keyed by key as a list.
def valuesOf(key, table): return list(set(map(lambda x: x[key], table)))

#########
# STATS #
#########

#UNTESTED
#calculate Fleiss' kappa from the table
#based on the old version, based on the Wikipedia article: 
#Fleiss' Kappa, circa 4 October 2011
#
#Takes a table of the sort that's been run through "pivotize"
def fKappa(valDicts):
	N = len(valDicts)
	n = lambda r: sum(r.values()) 
	
	#the old version of "pivotize" (it had a very different name)
	#did not recieve the same sort of pivot table. this compensates
	#for that discrepancy. 
	valDicts = map(lambda x: valDicts[x], valDicts)
	
	#totals of each col (i degenerates, j-axis expressed)
	#prepare for loop
	try: totals_i = map(lambda x: 0.0, range(0, len(valDicts[0])))
	except IndexError: print "What Kappa? More like what data."

	#this is used for consistency. if you do not have
	#all keys in each valDict, this will fail miserably.
	keyList = valDicts[0].keys() 
	#print keyList

	#traverse rows
	for each in valDicts:
		#add together all entries in each column
		rowVals = map(lambda k: each[k], keyList) #grab col vals in order
		totals_i = map(lambda t, r: t+float(r)/float(n(each)), \
				totals_i, rowVals)#add col vals 

	#combine the totals with their brethren	keys
	totals_i = dict(zip(keyList, totals_i))

	#totals of each row (j degenerates, i-axis expressed)	
	#prepare for loop
	totals_j = []
	#traverse rows
	for each in valDicts:
		totals_j += [sum(each.values())]

	#output check 1,2,1,2
	#for each in keyList:
	#	print str(each) + ": "+ str(totals_i[each])
	
	#calculate p_i values for each row
	p_i = []
	for each in valDicts:
		sumSqrs = sum(map(lambda x: x*x, each.values()))
		sums = sum(each.values())
		try:
			p_i += [float(sumSqrs - (sums))/float((sums)*(sums-1))]
		except ZeroDivisionError:
			p_i += [1.0]
	
	#calculate values
	#print totals_i
	p_js = map(lambda x: float(x)/float(N), totals_i.values()) 
	P_e = sum(map(lambda x: x*x, p_js))
	P = sum(p_i)/float(N)
	k = (P-P_e)/(1-P_e)
	
	#print "P_is:" + str(p_i)
	#print "P_j:" + str(p_js)
	#print "P_e: " + str(P_e)
	#print "P: " + str(P)
	
	return k

#Free Table:
# Calculate a contingency table from a free table and (r,c)
# see nltk.BigramAssocMeasures for more info
# location = (("row", "fart"), ("col", "butt)) or something similar
# (substitute row and col with appropriate key values
#
#tableSum - a function that gets the sum of the table
# OR you can find it before hand and pass a function like-- lambda x: 5000
def contingencyTable(wholeTable, location, 
        tableSum = lambda tab: sum(map(lambda y: y["value"], tab))):
    rowLabel, colLabel = location
    rowAlias, rowValue = rowLabel
    colAlias, colValue = colLabel
    
    row = filter(lambda x: x[rowAlias] == rowValue, wholeTable)
    col = filter(lambda x: x[colAlias] == colValue, wholeTable)
    
    print str((rowValue, colValue))
    print row

    #the value given by (rowValue, colValue)
    x_ii = filter(lambda x: x[colAlias] == colValue, row)[0]["value"]

    #I may have these swapped, but nbd
    x_io = sum(map(lambda x: x["value"], row)) - x_ii
    x_oi = sum(map(lambda x: x["value"], col)) - x_ii

    x_oo = tableSum(wholeTable) - x_io - x_oi - x_ii

    return (x_ii, (x_io, x_oi), x_oo)



    
