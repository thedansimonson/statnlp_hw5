from csv import reader
from DanLordOfTurk import loadTurkData, pivotize, fKappa, indexBy, simpleTable
from copy import copy
from random import shuffle
from math import log

#calculate cohen's kappa
def cKappa(matrix):
    vals = list(set(reduce(lambda x,y: list(x)+list(y), list(matrix))))
    diagVals = filter(lambda x: x[0]==x[1], list(matrix))

    rowTraverse = [[(x,y) for x in vals] for y in vals]
    colTraverse = [[(y,x) for x in vals] for y in vals]
    allCells = reduce(lambda x,y: x+y, rowTraverse)
    
    total = float(sum([matrix[c] for c in allCells]))

    #calculate probabilities for each row
    dirProb = lambda cellMap: [sum([matrix[c] for c in r])/total\
            for r in cellMap]
    rowProbs = dirProb(rowTraverse)
    colProbs = dirProb(colTraverse)


    p_a = sum([matrix[d] for d in diagVals])/total
    p_e = sum([x[0]*x[1] for x in zip(rowProbs, colProbs)])

    return (p_a-p_e)/(1.0-p_e)

#create a confusion matrix for cKappa
def confMatrix(data, parm, target):
    dataPairs = []
    dataByPos = indexBy("corpus_pos", data)
    for each in dataByPos:
        dataPairs.append(dict(map(lambda d: (d[parm],d[target]),\
                dataByPos[each])))
    
    #grab possible values for parms
    parms = list(dict(dataPairs[0]))
    if len(parms) != 2: return "Fail--parm doesn't have two values"
    
    #grab all target values
    targetValues = map(lambda d: d[target], data)
    targetValues = list(set(targetValues))
    targetValues.sort()

    #total up 
    matrix = dict([((v, w), 0) for v in targetValues for w in targetValues])
    for each in dataPairs:
        vals = tuple(map(lambda p: each[p], parms))
        matrix[vals]+=1
    
    return matrix

def histogram(stuff):
	theGram = {}
	for each in stuff:
		try:
			theGram[each] += 1
		except:
			theGram[each] = 1
	return theGram

#a list of words that extract() will like
def prepSentence(s): 
    s = s.lower().strip("<> ").split(" ")
    return ["BEG", "BEG"]+s+["END", "END"]
#from words s, return the context of word w b words before and a words after
extract = lambda s, b, w, a: s[s.index(w)-b:s.index(w)+(a+1)]

#mark locations of words in context (assuming distribution around center)
def markLocations(wbs):
    contextSize = (len(wbs[0])-1)/2

    prewords = [b[:contextSize] for b in wbs]
    postwords = [b[len(b)-contextSize:] for b in wbs]

    prewords = [zip(range(-contextSize, 0), b) for b in prewords]
    postwords = [zip(range(1,contextSize+1), b) for b in postwords]
    
    prewords = reduce(lambda x,y: x+y, prewords)
    postwords = reduce(lambda x,y: x+y, postwords)
    
    return prewords+postwords

#returns a trained Naive Bayes classifier function
# Manning and Schuetze (page 238)
def generateBayes(w, data, senseLocation, tokenLocation, contextSize = 2):
    allSenses = indexBy(senseLocation, data)
    
    #get word bags
    wordBags = dict([(s, []) for s in allSenses])
    for each in allSenses:
        sentences = [x[tokenLocation] for x in allSenses[each]]
        sentences = filter(lambda x: w in x, sentences)
        contexts = [extract(prepSentence(x), contextSize, w, contextSize)\
                for x in sentences]
        wordBags[each] = contexts

    #bind words to their relative positions to w
    # originally, C(v_j, s_k) -- l factors in locational information
    locWords = dict([(s, []) for s in allSenses])
    for each in wordBags:
        wbs = wordBags[each]
        if len(wbs) < 1: 
            del locWords[each]
            continue
        locWords[each] = markLocations(wbs)
        

    #first loop from training algorithm
    #calculates P(v_j|s_k)
    # represented in python as Pbayes[s_k][v_j]
    # ie, the bayesian probability, given sense k, of vocab item j
    rawWords = reduce(lambda x,y: x+locWords[y], [[]]+list(locWords))
    words = histogram(rawWords)
    smooth = 0.5
    Pbayes = dict([(s, dict([(w, smooth) for w in words])) for s in locWords])
    for s_k in locWords:
        localCounts = histogram(locWords[s_k])
        for each in localCounts: 
            Pbayes[s_k][each] += localCounts[each]
            Pbayes[s_k][each] = Pbayes[s_k][each]/words[each]
    
    Psense = {}
    totalSenstances = reduce(lambda x,y: x+len(locWords[y]), [0]+list(locWords))
    for s_k in locWords: 
        Psense[s_k] = float(len(locWords[s_k]))/totalSenstances

    return lambda c: bayesDisambiguator(Pbayes, Psense, smooth, c)

#wrapped in a lambda by generateBayes
log2 = lambda x: log(x)/log(2)
def bayesDisambiguator(P_Gsense_word, Psense, smooth, c):
    scores = {}
    #for each in P_Gsense_word: print P_Gsense_word[each]
    for s_k in Psense:
        scores[s_k] = log2(Psense[s_k])
        for v_j in c:
            try:
                scores[s_k] += log2(P_Gsense_word[s_k][v_j])
            except KeyError:
                scores[s_k] += log2(smooth)
    
    #argmax
    scores = scores.items()
    scores.sort(key=lambda x: x[1])
    return scores[-1][0]

#statistics
#http://en.wikipedia.org/wiki/Precision_and_recall
def expObsTable(expObsPairs):
    expects = list(set([x[0] for x in expObsPairs]+[x[1] for x in expObsPairs]))
    
    tables = dict([(x,{"tp": 0.0, "fp": 0.0, "fn": 0.0}) for x in expects])
    
    for each in expObsPairs:
        exp, obs = each
        if exp == obs: tables[exp]["tp"] += 1
        else:
            tables[exp]["fn"] += 1
            tables[obs]["fp"] += 1

    return tables

def precision(data, gold, test):
    relevantNums = [(x[gold], x[test]) for x in data]
    tables = expObsTable(relevantNums)
    values = []
    for x in tables: 
        try:
            values.append((x,tables[x]["tp"]/(tables[x]["tp"]+tables[x]["fp"])))
        except:
            values.append((x, -1))
    return dict(values)

def recall(data, gold, test):
    relevantNums = [(x[gold], x[test]) for x in data]
    tables = expObsTable(relevantNums)
    values = dict([(x, tables[x]["tp"]/(tables[x]["tp"]+tables[x]["fn"])) \
            for x in tables])
    return values

###################
# Actual Script
###################

data = loadTurkData(["partyNN.csv"])

cleanData = []
for each in data:
    each["token"] = each["token"].strip("<> \'\"")
    cleanData.append(each)

pivot = pivotize("corpus_pos", "value", cleanData)
print fKappa(pivot)

################
#Cohen's kappas#
################
items = indexBy("corpus_pos", cleanData)

#find pairs of annotators
annotatorPairs = {}
for each in items:
    annotatorPair = map(lambda x: x["annotator"], items[each])
    annotatorPair.sort()
    if tuple(annotatorPair) not in annotatorPairs:
        annotatorPairs[tuple(annotatorPair)] = items[each]
    else:
        annotatorPairs[tuple(annotatorPair)] += items[each]

confusionMatrices = dict(map(lambda p: (p, confMatrix(annotatorPairs[p],\
        "annotator", "value")), annotatorPairs))

cKappa = [(p, cKappa(confusionMatrices[p])) for p in confusionMatrices]
for each in cKappa: print str(each)

###############
# Naive Bayes #
###############
dataRaw = [x for x in reader(open("partyNN.csv"))]
dataRaw = simpleTable(dataRaw[0], dataRaw[1:])
dataAgrees = filter(lambda x: x["value1"] == x["value2"], dataRaw)

#simplify data
dataAgrees = [{"value": x["value1"], "token": x["token"]} for x in dataAgrees]

#split into training, execution sets
shuffle(dataAgrees)
testData = dataAgrees[:15]
trainingData = dataAgrees[15:]

#do the test!
naiveBayes = generateBayes("party", trainingData, "value", "token")
for each in testData:
    token = prepSentence(each["token"])
    if "party" not in token: continue
    context = markLocations(extract(token, 2, "party", 2))
    each["result"] = naiveBayes(context)

for each in testData: print each

prec = precision(testData, "value", "result")
rec = recall(testData, "value", "result")

print "Precision"
for each in prec: print each +": "+str(prec[each])
print "\nRecall"
for each in rec: print each +": "+str(rec[each])


#for each in annotatorPairs: print str(each) + ": " + str(annotatorPairs[each])
    

#for each in pivot: print str(each) + ": " + str(pivot[each])

"""
Results:
I was a bit confused by the "compute the Cohen kappa-score for the sentences 
that you annotated and for the entire annotation as a whole." I get computing 
the kappa for an individual vs others, but it's weird to use Cohen's kappa for
the whole table. Therefore, I've interprted the question as "calculate 
Cohen's Kappa for every pair of annotators."

Fleiss' Kappa for the whole table is: 0.930429597237
That's really good. 

As for the Cohen's kappas:
(('des62', 'sds72'), 0.75)
(('anw36', 'des62'), 1.0)
(('akm66', 'klh58'), 0.9391727493917275)
(('dg338', 'tc374'), 1.0)
(('klh58', 'tc374'), 0.9342105263157894)
(('akm66', 'sds72'), 0.8697916666666665)
(('anw36', 'dg338'), 1.0)

As for the categorization task, the precision and recall numbers vary wildly 
from run-to-run as a result of changes in the test set. Frequently, division
by zero errors crop up (due to a combination of no tp and no fp/fn); these are
marked with -1.

                Different Random Test Selections
Precision       1: -1     1: 0.6666 1: 0.3333 1: 0.22222
                3: 0.3571 3: 0.6    3: 0.5    3: 0.5
                2: 0.0    2: 0.5    2: -1     2: -1
                                              
Recall          1: 0.0    1: 0.3333 1: 0.6    1: 1.0
                3: 1.0    3: 0.8571 3: 0.5    3: 0.42857
                2: 0.0    2: 0.5    2: 0.0    2: 0.0    
"""


