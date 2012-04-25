from nltk.corpus import treebank
from nltk import Tree
from math import log

#find the highest node of type xNode
#tree is of type tree
#xNode is a string identifying the type of tree
#@returns (depth, subtree)
#
#Note that this is broad in node scope--ie, xNode = "NP" returns
#nodes of type "NP" and "NP-SBJ" etc.
leaf = (9999, "leaf")
def getHighestXNode(xNode, tree, depth = 0, sortMethod = lambda x: x[0]):
    try:
        if xNode == tree.node[:6]: return (depth, tree)
    except:
        return leaf
    #dig through the tree
    nextNodes = lambda lt: getHighestXNode(xNode, lt, depth = depth+1)
    results = map(nextNodes, list(tree))

    #find best match
    if not results: return (9999, "no value found")
    results.sort(key=sortMethod)
    return results[0]

#runs multiple nodes through getHighestXNode()
def getHighestXNodes(xNodes, tree, depth = 0, sortMethod = lambda x: x[0]):
    results = map(lambda n: getHighestXNode(n, tree, depth=depth), xNodes)
    results.sort(key=lambda x: x[0])
    return results[0]

#return true if tree contains a common noun
#
#note that this has narrow scope--targetNodes = ["NN"] only returns
#True if there is a node of type NN in the tree
def containsType(tree, targetNodes):
    #if we found a leaf, abandon ship
    try:
        node = tree.node
    except:
        return False

    #found what we're looking for
    if node in targetNodes: return True 

    #search deeper
    lowerNodes = map(lambda t: containsType(t, targetNodes),list(tree))
    inLowerNodes = reduce(lambda x,y: x or y, lowerNodes)
    return inLowerNodes
    
#extract right-most NN or NNS from Ntypes
Ntypes = ["NN", "NNS"]
def extractSubjectHead(xpList):
    head = xpList.pop()
    if head[1] in Ntypes: return head
    else: return extractSubjectHead(xpList)

#extract VP-head
Vtypes = ["VB", "VBZ", "VBD", "VBN", "VBP", "VBG"] #another lousy hack
def extractVPhead(vpTree):
    children = list(vpTree)
    children = dict(map(lambda t: (t.node, t), children))
    
    #in this case, we're probably at a (VP (MD ...) (VP ...))
    #or some other funky structure.
    if "VP" in children:
        vpHead = extractVPhead(children["VP"])
        #if the lower levels return an error, we need to 
        #we won't return their result, but try to grab a VBX at this level
        if vpHead[0] != "error":
            return vpHead

    #if we didn't find another VP nested in the higher VP, we're looking
    #for the VB we came for
    for each in Vtypes:
        if each in children: 
            return children[each].pos()[0] 

    #we shouldn't reach this case
    return ("error", "extract at current level")

def histogram(stuff):
	theGram = {}
	for each in stuff:
		try:
			theGram[each] += 1
		except:
			theGram[each] = 1
	return theGram

#KL divergence
log2 = lambda x: log(x)/log(2)
def klDiv(p, q):
	formula = lambda y: p[y]*log2(p[y]/q[y])
	value = 0.0
	for each in p:
		try:
			value += formula(each)
		except:
			pass
	return value

#M&S page 289, formula (8.28)
def selectPref(v, pairwise, C):
    formula = lambda pair: pairwise[pair]*log2(pairwise[pair]/C[p[0]])
    results = []
    for each in C:
        p = (each, v)
        try:
            results.append(formula(p))
        except KeyError:
            pass
    return sum(results)
        
#load trees
print "Loading treebank."
sentenceTrees = map(lambda x: x, treebank.parsed_sents())
print "Finding nested sentences"
sentenceTrees = reduce(lambda x,y: x+\
        filter(lambda z: z.node == "S", y.subtrees()), [[]]+sentenceTrees)

#subjects
topNP = lambda t: getHighestXNode("NP-SBJ", t)
subjects = map(lambda t: topNP(t)[1], sentenceTrees)

#verbs
topVP = lambda t: getHighestXNode("VP", t)
verbs = map(lambda t: topVP(t)[1], sentenceTrees)

sentTriples = zip(sentenceTrees, subjects, verbs)

#remove sentences that returned "leaf" (did not contain subject or verb)
sentTriples=filter(lambda x: x[1] != "leaf" and x[2] != "leaf", sentTriples)

#only keep common nouns
sentTriples = filter(lambda t: containsType(t[1], Ntypes), sentTriples)

#find subject heads
sentTriples = map(lambda x: (x[0], extractSubjectHead(list(x[1].pos()))\
        , x[2]), sentTriples)

#find verb heads
sentTriples = map(lambda x: (x[0], x[1], extractVPhead(x[2])), sentTriples)

#remove sentences for which there was no verb head found (~17)
sentTriples = filter(lambda x: x[2][0]!="error", sentTriples)

#count everything
f_nouns = histogram(map(lambda x: x[1][0], sentTriples))
f_verbs = histogram(map(lambda x: x[2][0], sentTriples))
f_pairs = histogram(map(lambda x: (x[1][0], x[2][0]), sentTriples))

#turn counts to probabilities
total = float(len(sentTriples))
probabilitize = lambda x: (x[0], x[1]/total)
p_nouns = dict(map(probabilitize,f_nouns.items()))
p_verbs = dict(map(probabilitize,f_verbs.items()))
p_joint = dict(map(probabilitize,f_pairs.items()))
p_bayes = dict(map(lambda x: (x, p_joint[x]/p_verbs[x[1]]) , p_joint))

#calculate selection preferences
preference = {}
for each in p_verbs: preference[each] = selectPref(each, p_bayes, p_nouns)

#display sorted results
preferences = preference.items()
preferences.sort(key=lambda x: x[1])
for each in preferences: 
    word, pref = each
    print word +": "+ str(pref)

"""
Results:

Loading treebank.
Finding nested sentences
said: 2.33999398452
is: 2.89074654857
are: 3.49142369604
rose: 3.84605957661
was: 3.89545101784
have: 4.24899679077
be: 4.34529240256
were: 4.35827535176
doing: 4.53404421329
had: 4.54631805262
say: 4.57509305622
fell: 4.7286214036
asking: 4.79301548279
contesting: 4.79301548279
targets: 4.79301548279
supplies: 4.79301548279
cited: 4.79301548279
chosen: 4.79301548279
offers: 4.79301548279
disclose: 4.79301548279
generate: 4.79301548279
adopted: 4.79301548279
acknowledges: 4.79301548279
holds: 4.79301548279
operating: 4.79301548279
uses: 4.79301548279
expand: 4.79301548279
experienced: 4.79301548279
export: 4.79301548279
riding: 4.79301548279
lent: 4.79301548279
begin: 4.97435871864
expects: 4.99891553943
turn: 5.01171813894
reported: 5.02573716661
gained: 5.0412400412
says: 5.08553656386
sold: 5.19030359265
closed: 5.22439148237
added: 5.30516947064
offered: 5.30681669487
formed: 5.3507540915
indicated: 5.36904478023
noted: 5.44360239095
get: 5.46555382838
feel: 5.51171813894
been: 5.51789729035
open: 5.57448357998
increased: 5.57514137705
withdrawn: 5.62051321673
stand: 5.63521534911
expected: 5.64225352083
began: 5.64855241596
maintained: 5.65245218754
showed: 5.65777260546
do: 5.69651673938
has: 5.70405468688
took: 5.76950894849
continues: 5.79775908251
named: 5.8068936994
includes: 5.82317749739
estimated: 5.89185822108
forecast: 5.92066799221
resist: 5.94296637706
elected: 5.95449656993
eased: 5.95826053698
posted: 5.96789496705
received: 5.97605520326
dropped: 6.01576256577
plans: 6.01806157604
soared: 6.01958874458
take: 6.0271936822
want: 6.07026003129
pay: 6.10494611213
based: 6.13671645803
knows: 6.14323534186
go: 6.16509326854
ended: 6.1719464612
considering: 6.17268218638
believe: 6.17891135745
set: 6.18542084921
found: 6.20248762033
asked: 6.21821078899
totaled: 6.22165543567
jump: 6.22238720167
transformed: 6.22792045456
called: 6.26514822264
decided: 6.27043021014
make: 6.27920948989
continued: 6.27957360089
approved: 6.31340227173
scrambled: 6.31820657738
agreed: 6.32470890962
remains: 6.3497051724
retain: 6.39420812411
changed: 6.39694561095
continue: 6.42812392989
financed: 6.47795818086
risk: 6.49368255427
attributed: 6.4996565236
believes: 6.51171813894
become: 6.5357684454
increase: 6.54465662871
acquired: 6.54869281272
included: 6.55839226046
include: 6.56129761778
earned: 6.56751557557
turned: 6.59600401388
taken: 6.59767244484
tripled: 6.61922458442
think: 6.62101163774
note: 6.63222218869
priced: 6.63329207038
completed: 6.6386296642
fall: 6.64733476665
trade: 6.65804414079
rise: 6.65876836197
leave: 6.67268218638
growing: 6.68170821221
told: 6.68234899437
decline: 6.68280577574
faltered: 6.68610027887
skidded: 6.68610027887
bolstered: 6.68610027887
reeling: 6.68610027887
recovered: 6.68610027887
gyrate: 6.68610027887
disappointed: 6.68668937447
finished: 6.69148198802
result: 6.70503814902
divided: 6.70822373541
made: 6.7183298461
traded: 6.72549737541
expecting: 6.72792045456
care: 6.72792045456
tanked: 6.72792045456
opening: 6.72792045456
deliver: 6.72792045456
awaits: 6.72792045456
flooded: 6.72792045456
heading: 6.72792045456
having: 6.72792045456
kept: 6.72930931883
reflect: 6.75074178734
raised: 6.75772929438
exceed: 6.75885904982
advanced: 6.77064752225
cautioned: 6.77098917646
crossed: 6.77098917646
escaped: 6.77098917646
answer: 6.77098917646
portray: 6.77098917646
wallowing: 6.77098917646
enjoy: 6.77098917646
place: 6.77098917646
respond: 6.77098917646
comment: 6.77098917646
voice: 6.77098917646
seize: 6.77098917646
tendered: 6.77098917646
ignored: 6.77098917646
plan: 6.77098917646
curb: 6.77098917646
paid: 6.78443152337
give: 6.79143341528
run: 6.79508458166
jumped: 6.80338039106
profit: 6.8041993893
move: 6.8108987838
expelled: 6.81820657738
urged: 6.81892281156
hit: 6.83349315386
contracted: 6.85297704401
come: 6.85340379455
edged: 6.86193799801
occur: 6.86495620608
came: 6.87991257726
charged: 6.88020093602
raise: 6.88162793827
fallen: 6.8817182996
opposed: 6.88950877511
redeploy: 6.90849270021
acquires: 6.90849270021
fault: 6.90849270021
escalated: 6.90849270021
buying: 6.90849270021
spent: 6.94242002173
needed: 6.95894235408
balked: 6.96516343674
skyrocketed: 6.9787916277
proposed: 6.99854876371
giving: 7.00627901444
resulting: 7.00802837376
retraced: 7.00802837376
anticipated: 7.00802837376
rated: 7.00802837376
points: 7.00802837376
repriced: 7.00802837376
played: 7.00802837376
diversify: 7.00802837376
drew: 7.00802837376
like: 7.00982809584
announced: 7.01354764134
seek: 7.04171255289
offer: 7.04617939655
appears: 7.04617939655
devoted: 7.06049579365
pursue: 7.06049579365
ranked: 7.06049579365
fail: 7.06049579365
brushed: 7.06049579365
amass: 7.06049579365
contribute: 7.06049579365
capture: 7.06049579365
charges: 7.06148597571
climbed: 7.06646976298
accused: 7.06892281156
disclosed: 7.07421130625
declined: 7.07450769992
indicates: 7.09964832083
placed: 7.09964832083
collapsed: 7.11068782774
propagandizes: 7.11494357767
telling: 7.11494357767
plays: 7.11494357767
disappear: 7.11494357767
explains: 7.11494357767
resumes: 7.11494357767
fined: 7.11494357767
maintaining: 7.11494357767
lifted: 7.11494357767
veto: 7.11494357767
curtailed: 7.11494357767
creates: 7.11494357767
caught: 7.11494357767
echoed: 7.11494357767
asserts: 7.11494357767
increases: 7.11494357767
excise: 7.11494357767
assert: 7.11494357767
threatens: 7.11494357767
act: 7.11494357767
propagandize: 7.11494357767
minted: 7.11494357767
curbed: 7.11494357767
looking: 7.14694561095
prompted: 7.15217205256
led: 7.15897013253
reflected: 7.16386334681
seem: 7.16922797827
surged: 7.17482268976
trailed: 7.18732645611
assembled: 7.23042079509
merged: 7.23042079509
pine: 7.23042079509
bankroll: 7.23042079509
competed: 7.23042079509
accusing: 7.23042079509
clobbered: 7.23042079509
wasted: 7.23042079509
undercut: 7.23042079509
exhaust: 7.23042079509
starting: 7.23042079509
aiming: 7.23042079509
moving: 7.23042079509
analyze: 7.23042079509
consented: 7.23190119455
reached: 7.23417013763
allowed: 7.2440327411
increasing: 7.24410708123
supported: 7.25074178734
require: 7.25154148209
failed: 7.27858206458
saw: 7.28297068062
used: 7.28670066209
disturbs: 7.29182133976
swapped: 7.29182133976
embroiled: 7.29182133976
printed: 7.29182133976
trades: 7.29182133976
heating: 7.29182133976
relaunched: 7.29182133976
slow: 7.29318623613
proved: 7.29318623613
tumbled: 7.29318623613
apply: 7.30220917991
bought: 7.3041993893
use: 7.33970481044
help: 7.35766103359
reduce: 7.36131069051
suspended: 7.36131069051
entered: 7.36193799801
improve: 7.36922458442
hopes: 7.37106946702
goes: 7.39983011051
sell: 7.4044004898
expanded: 7.41061025555
cause: 7.42268218638
boosted: 7.43078134618
became: 7.44769146283
caused: 7.4534577788
change: 7.49058129122
warn: 7.49345520093
speculating: 7.49345520093
questioned: 7.49345520093
know: 7.4940327411
find: 7.49799921623
quoted: 7.49913659887
hope: 7.50070498577
suggests: 7.5154652096
consider: 7.52065978944
remained: 7.52165187519
yielding: 7.52290204545
build: 7.52290204545
taking: 7.5435175855
filed: 7.54420828826
replaced: 7.55629819075
doubled: 7.55629819075
suggest: 7.56945674765
live: 7.56945674765
identified: 7.57132748726
face: 7.58026359706
buy: 7.61193799801
gives: 7.61368084207
ranged: 7.62548520035
given: 7.62582706469
lowered: 7.63468141302
moderated: 7.63937439285
lack: 7.64545829437
tracks: 7.64545829437
notched: 7.64545829437
identify: 7.64545829437
crying: 7.64545829437
invested: 7.64545829437
let: 7.64993877137
slowing: 7.65441924837
contained: 7.67268218638
avoid: 7.67268218638
got: 7.67809208152
slipped: 7.68246873183
held: 7.68502982884
confirmed: 7.72716246032
stretching: 7.72792045456
reaped: 7.72792045456
rebound: 7.72792045456
stepping: 7.72792045456
joins: 7.72792045456
earns: 7.72792045456
fighting: 7.72792045456
redeemed: 7.72792045456
commit: 7.72792045456
inched: 7.73042079509
extend: 7.73042079509
paying: 7.73042079509
hurt: 7.73069896268
settled: 7.73313642965
takes: 7.73561543153
plunged: 7.73800413789
attend: 7.75074178734
operate: 7.75074178734
complained: 7.77498005701
remain: 7.79219401058
rushed: 7.79318623613
expect: 7.79617939655
begins: 7.8019533888
put: 7.81370646254
valued: 7.81538329581
materialized: 7.81538329581
shopped: 7.81538329581
leading: 7.81538329581
gotten: 7.81538329581
report: 7.81538329581
parallels: 7.81538329581
erodes: 7.81538329581
handled: 7.81538329581
awarded: 7.81538329581
allow: 7.82081456493
trying: 7.82674333406
need: 7.82906958195
covered: 7.83053001348
threatened: 7.84456253472
grew: 7.85947020064
comes: 7.87148226274
designed: 7.88428486225
keep: 7.88963152408
consist: 7.88963152408
becomes: 7.89708746176
stood: 7.90441924837
requires: 7.90466082059
managed: 7.90849270021
materialize: 7.90849270021
hold: 7.90849270021
restructured: 7.90849270021
executes: 7.90849270021
climb: 7.90849270021
vowed: 7.90849270021
sees: 7.90849270021
blurred: 7.90849270021
specializes: 7.90849270021
record: 7.90849270021
setting: 7.90849270021
introduces: 7.90849270021
predicting: 7.90849270021
slid: 7.91170583478
stopped: 7.92812392989
calls: 7.92812392989
shows: 7.93793954473
rising: 7.95258051786
lacks: 7.96516343674
add: 7.97917062483
join: 8.00802837376
suspects: 8.00802837376
confirms: 8.00802837376
block: 8.00802837376
promise: 8.00802837376
touch: 8.02290204545
look: 8.03306254158
sparked: 8.03543329485
compared: 8.03543329485
concluded: 8.06646976298
speculated: 8.06646976298
prove: 8.08866064691
trading: 8.11494357767
bowed: 8.11494357767
combines: 8.11494357767
reward: 8.11494357767
chooses: 8.11494357767
proving: 8.1171374608
ran: 8.1171374608
refused: 8.13198421651
described: 8.14247770049
spurred: 8.15441924837
pushed: 8.17377912794
went: 8.19508458166
rejected: 8.20052539115
argue: 8.21562275531
suggested: 8.21730394012
seemed: 8.22548520035
followed: 8.22906958195
offset: 8.22906958195
abandon: 8.23042079509
involved: 8.23042079509
relies: 8.23042079509
derived: 8.23042079509
raises: 8.23042079509
trail: 8.23042079509
lost: 8.23799415393
tend: 8.25074178734
reduced: 8.26145726322
helped: 8.26759859754
scheduled: 8.26946765926
becoming: 8.27165187519
expanding: 8.29318623613
insist: 8.29318623613
appeared: 8.29463582107
cut: 8.29959371164
approve: 8.30226644084
grown: 8.31212496104
contain: 8.31538329581
resigned: 8.31538329581
wrote: 8.33866064691
crippled: 8.35595167718
upheld: 8.35595167718
disagreed: 8.35595167718
orders: 8.35595167718
regulated: 8.35595167718
looks: 8.35595167718
drawn: 8.36193799801
cost: 8.36876662819
drove: 8.41170583478
worried: 8.41170583478
won: 8.41170583478
leaves: 8.43793954473
losing: 8.43793954473
throws: 8.43793954473
watch: 8.43793954473
provided: 8.43793954473
force: 8.44242002173
makes: 8.45644476346
boost: 8.49345520093
explained: 8.49345520093
locked: 8.49345520093
conducted: 8.49345520093
weaken: 8.49345520093
exceeded: 8.49345520093
disciplined: 8.49345520093
gauge: 8.49345520093
averaged: 8.49345520093
sagged: 8.49345520093
polled: 8.49345520093
outpaced: 8.49345520093
carried: 8.49345520093
amounted: 8.49345520093
stare: 8.49345520093
skip: 8.49345520093
recede: 8.49345520093
sank: 8.49345520093
read: 8.50711246128
work: 8.52065978944
walk: 8.52065978944
account: 8.52290204545
turning: 8.52290204545
registered: 8.52290204545
surfaced: 8.52290204545
rolled: 8.55360231779
returned: 8.56375412843
reflects: 8.56375412843
succeed: 8.56375412843
ordered: 8.58566748649
snapped: 8.59479059656
represent: 8.59508458166
required: 8.6135445653
going: 8.6144730163
prevent: 8.61922458442
appear: 8.61922458442
stepped: 8.61922458442
triggered: 8.62796915441
calculate: 8.64545829437
underscore: 8.64545829437
leveling: 8.64545829437
prefer: 8.64545829437
intend: 8.64545829437
enacted: 8.64545829437
applaud: 8.64545829437
attended: 8.64545829437
outnumbered: 8.64545829437
appeal: 8.64545829437
ban: 8.64545829437
headed: 8.64545829437
ushering: 8.64545829437
befuddled: 8.64545829437
despised: 8.64545829437
reasserts: 8.64545829437
urging: 8.64545829437
defines: 8.64545829437
barred: 8.64545829437
holding: 8.64545829437
struggling: 8.65441924837
getting: 8.65947020064
featured: 8.73042079509
follow: 8.73042079509
gave: 8.73042079509
falling: 8.77165187519
built: 8.77290204545
meet: 8.7897780968
coming: 8.7897780968
lead: 8.7897780968
sound: 8.81538329581
solved: 8.81538329581
eclipse: 8.81538329581
centers: 8.81538329581
waiting: 8.81538329581
involves: 8.81538329581
color: 8.81538329581
started: 8.81538329581
challenge: 8.81538329581
evolved: 8.81538329581
stemmed: 8.81538329581
talk: 8.81538329581
pealing: 8.81538329581
starts: 8.81538329581
sounding: 8.81538329581
weigh: 8.81538329581
joining: 8.81538329581
nullified: 8.81538329581
spur: 8.81538329581
rung: 8.81538329581
rumored: 8.81538329581
declining: 8.81538329581
wants: 8.81538329581
predicated: 8.81538329581
overcome: 8.81538329581
signals: 8.81538329581
follows: 8.81538329581
trust: 8.81538329581
accepted: 8.81538329581
propelling: 8.81538329581
restored: 8.81538329581
stop: 8.84044579461
kicked: 8.86193799801
concentrated: 8.86193799801
scrambling: 8.91170583478
suffer: 8.91170583478
laughing: 8.91170583478
runs: 8.92812392989
created: 8.96130248774
show: 8.98490127209
reopened: 9.00802837376
keeping: 9.00802837376
imposing: 9.00802837376
ignoring: 9.00802837376
decries: 9.00802837376
keeps: 9.00802837376
pending: 9.00802837376
pins: 9.00802837376
profess: 9.00802837376
talked: 9.00802837376
undergoing: 9.00802837376
interviewed: 9.00802837376
worsen: 9.00802837376
overpriced: 9.00802837376
attempts: 9.00802837376
meant: 9.00802837376
yield: 9.00802837376
draws: 9.00802837376
spark: 9.00802837376
predispose: 9.00802837376
choose: 9.00802837376
inhibit: 9.00802837376
lapses: 9.00802837376
broken: 9.00802837376
drifted: 9.00802837376
afford: 9.00802837376
requested: 9.00802837376
viewed: 9.02290204545
bring: 9.02290204545
feels: 9.02290204545
sells: 9.02290204545
carries: 9.02290204545
shipped: 9.02551751372
believed: 9.03543329485
surrendered: 9.03543329485
violate: 9.03543329485
receive: 9.06538329581
launched: 9.06538329581
enters: 9.08566748649
owns: 9.08566748649
total: 9.12311143013
beginning: 9.15441924837
ruled: 9.15441924837
fueled: 9.15441924837
eliminated: 9.15441924837
squeezed: 9.15441924837
seems: 9.16914267063
working: 9.17377912794
hugging: 9.23042079509
quipped: 9.23042079509
drooled: 9.23042079509
compressed: 9.23042079509
asks: 9.23042079509
wish: 9.23042079509
reviewing: 9.23042079509
varied: 9.23042079509
suspend: 9.23042079509
equip: 9.23042079509
grapple: 9.23042079509
teach: 9.23042079509
exhibited: 9.23042079509
merit: 9.23042079509
participate: 9.23042079509
handle: 9.23042079509
means: 9.23042079509
resent: 9.23042079509
concern: 9.23042079509
enabling: 9.23042079509
tightened: 9.23042079509
erect: 9.23042079509
retired: 9.23042079509
ease: 9.23042079509
facing: 9.23042079509
provides: 9.23042079509
prohibited: 9.23042079509
opens: 9.23042079509
regard: 9.23042079509
agree: 9.23042079509
play: 9.23042079509
dominated: 9.23042079509
left: 9.23042079509
introduced: 9.29463582107
produce: 9.31538329581
tried: 9.31538329581
carry: 9.31538329581
matched: 9.31538329581
dumped: 9.31538329581
delivered: 9.31538329581
continuing: 9.31538329581
looming: 9.31538329581
promises: 9.31538329581
improving: 9.31538329581
expire: 9.31538329581
considered: 9.36876662819
charge: 9.41170583478
tested: 9.41170583478
needs: 9.41170583478
fare: 9.41170583478
passed: 9.41170583478
did: 9.49345520093
posts: 9.49345520093
sidestep: 9.49345520093
contrast: 9.49345520093
deemed: 9.49345520093
intended: 9.49345520093
demanding: 9.49345520093
developed: 9.49345520093
produced: 9.49345520093
try: 9.49345520093
denied: 9.49345520093
print: 9.49345520093
scrounge: 9.49345520093
accompany: 9.49345520093
refuse: 9.49345520093
target: 9.49345520093
implemented: 9.49345520093
recommended: 9.49345520093
absorbed: 9.49345520093
discourage: 9.49345520093
criticized: 9.49345520093
enhances: 9.49345520093
declines: 9.49345520093
violated: 9.49345520093
reallocated: 9.49345520093
acquiring: 9.49345520093
adjusted: 9.49345520093
rebuild: 9.49345520093
renewed: 9.49345520093
restructure: 9.49345520093
assigned: 9.49345520093
represents: 9.49345520093
concentrate: 9.49345520093
confirm: 9.49345520093
does: 9.49345520093
reaching: 9.49345520093
assumed: 9.49345520093
question: 9.49345520093
directed: 9.49345520093
pull: 9.49345520093
signed: 9.49345520093
check: 9.49345520093
thought: 9.52290204545
fold: 9.52290204545
joined: 9.52290204545
sought: 9.56375412843
seen: 9.56375412843
gets: 9.56375412843
marketed: 9.56375412843
pumping: 9.65441924837
focused: 9.65441924837
opened: 9.70209996152
see: 9.70209996152
tote: 9.81538329581
illustrates: 9.81538329581
sent: 9.81538329581
presented: 9.81538329581
clicked: 9.81538329581
decrease: 9.81538329581
heard: 9.81538329581
share: 9.81538329581
end: 9.81538329581
hampered: 9.81538329581
delayed: 9.81538329581
happened: 9.81538329581
disapprove: 9.81538329581
characterized: 9.81538329581
extended: 9.81538329581
abide: 9.81538329581
retained: 9.81538329581
store: 9.81538329581
focusing: 9.81538329581
stifle: 9.81538329581
lengthened: 9.81538329581
prohibits: 9.81538329581
destroy: 9.81538329581
cleared: 9.81538329581
responded: 9.81538329581
breathed: 9.81538329581
judged: 9.81538329581
fixed: 9.81538329581
espouse: 9.81538329581
wear: 9.81538329581
evaporated: 9.81538329581
understand: 9.81538329581
proven: 9.81538329581
worked: 9.81538329581
granted: 9.81538329581
forced: 9.81538329581
blamed: 9.81538329581
point: 9.81538329581
redeem: 9.81538329581
steps: 9.81538329581
contradict: 9.81538329581
works: 9.81538329581
fretted: 9.81538329581
knew: 9.81538329581
mean: 9.81538329581
pitches: 9.81538329581
searching: 9.81538329581
prevents: 9.81538329581
view: 9.81538329581
realize: 9.81538329581
tailored: 9.81538329581
interested: 9.81538329581
resembles: 9.81538329581
eliminates: 9.81538329581
risen: 9.81538329581
casts: 9.81538329581
claim: 9.89708746176
replace: 10.0229020455
states: 10.0229020455
argued: 10.0229020455
die: 10.0229020455
omitted: 10.0229020455
determined: 10.0229020455
shrinks: 10.0229020455
covers: 10.0229020455
whipsaw: 10.2304207951
purrs: 10.2304207951
begot: 10.2304207951
notes: 10.2304207951
replicated: 10.2304207951
implement: 10.2304207951
carrying: 10.2304207951
talks: 10.2304207951
recall: 10.2304207951
provoke: 10.2304207951
influenced: 10.2304207951
fuming: 10.2304207951
crowded: 10.2304207951
welcomed: 10.2304207951
termed: 10.2304207951
disagrees: 10.2304207951
refuses: 10.2304207951
cultivated: 10.2304207951
occurs: 10.2304207951
undo: 10.2304207951
structured: 10.2304207951
interjects: 10.2304207951
fills: 10.2304207951
playing: 10.2304207951
walking: 10.2304207951
discovered: 10.2304207951
range: 10.2304207951
resisting: 10.2304207951
pegged: 10.2304207951
compare: 10.2304207951
operated: 10.2304207951
observed: 10.2304207951
state: 10.2304207951
abating: 10.2304207951
queuing: 10.2304207951
owed: 10.2304207951
limping: 10.2304207951
claimed: 10.2304207951
comments: 10.2304207951
protected: 10.2304207951
numbered: 10.2304207951
spend: 10.2304207951
plagued: 10.2304207951
performing: 10.2304207951
deal: 10.2304207951
scared: 10.2304207951
ventilated: 10.2304207951
narrowed: 10.2304207951
forgiven: 10.2304207951
discussed: 10.2304207951
gloss: 10.2304207951
concede: 10.2304207951
chastised: 10.2304207951
compel: 10.2304207951
topped: 10.2304207951
describe: 10.2304207951
transfers: 10.2304207951
compete: 10.2304207951
provide: 10.2304207951
grows: 10.2304207951
turns: 10.3153832958
attract: 10.3153832958
damaged: 10.3153832958
dismissed: 10.3153832958
wanted: 10.3153832958
diminished: 10.3153832958
convicted: 10.3153832958
stored: 10.3153832958
endorsed: 10.3153832958
repaid: 10.3153832958
start: 10.3153832958
shrank: 10.3153832958
felt: 10.8153832958
answered: 10.8153832958
bribed: 10.8153832958
marks: 10.8153832958
suffered: 10.8153832958
abandoned: 10.8153832958
perpetuates: 10.8153832958
offering: 10.8153832958
tempts: 10.8153832958
zoomed: 10.8153832958
pushing: 10.8153832958
equals: 10.8153832958
represented: 10.8153832958
engage: 10.8153832958
postponed: 10.8153832958
emerge: 10.8153832958
aimed: 10.8153832958
counts: 10.8153832958
spook: 10.8153832958
occurred: 10.8153832958
dislike: 10.8153832958
posing: 10.8153832958
fed: 10.8153832958
overstated: 10.8153832958
outlawed: 10.8153832958
suing: 10.8153832958
foundering: 10.8153832958
scoffs: 10.8153832958
executed: 10.8153832958
gauges: 10.8153832958
vary: 10.8153832958
exhibits: 10.8153832958
hurting: 10.8153832958
return: 10.8153832958
sweeping: 10.8153832958
impaired: 10.8153832958
mollified: 10.8153832958
overused: 10.8153832958
merge: 10.8153832958
thwart: 10.8153832958
dominates: 10.8153832958
behaving: 10.8153832958
assured: 10.8153832958
averted: 10.8153832958
oppose: 10.8153832958
routes: 10.8153832958
chopped: 10.8153832958
benefited: 10.8153832958
notify: 10.8153832958
launch: 10.8153832958
limited: 10.8153832958
vested: 10.8153832958
instructed: 10.8153832958
causing: 10.8153832958
urge: 10.8153832958
wedded: 10.8153832958
pair: 10.8153832958
stands: 10.8153832958
employed: 10.8153832958
beat: 10.8153832958
denounce: 10.8153832958
enhanced: 10.8153832958
gored: 10.8153832958
interrogated: 10.8153832958
swim: 10.8153832958
underlying: 10.8153832958
predicted: 10.8153832958
steal: 10.8153832958
declared: 10.8153832958
bled: 10.8153832958
muted: 10.8153832958
exchange: 10.8153832958
ends: 10.8153832958
met: 10.8153832958
planned: 10.8153832958
assassinated: 10.8153832958
implied: 10.8153832958
catch: 10.8153832958
harms: 10.8153832958
chilled: 10.8153832958
commanded: 10.8153832958
entitles: 10.8153832958
discredit: 10.8153832958
split: 10.8153832958
magnified: 10.8153832958
costs: 10.8153832958
sets: 10.8153832958
claims: 10.8153832958
being: 10.8153832958
thinking: 10.8153832958
fared: 10.8153832958
arrest: 10.8153832958
belongs: 10.8153832958
bid: 10.8153832958
injuring: 10.8153832958
traced: 10.8153832958
harmed: 10.8153832958
exceeding: 10.8153832958
resonate: 10.8153832958
contributing: 10.8153832958
eliminate: 10.8153832958
permitted: 10.8153832958
cranked: 10.8153832958
renew: 10.8153832958
mixed: 10.8153832958
alleged: 10.8153832958
resulted: 10.8153832958
exhausted: 10.8153832958
ship: 10.8153832958
amounts: 10.8153832958
compares: 10.8153832958
test: 10.8153832958
preapproved: 10.8153832958
helping: 10.8153832958
died: 10.8153832958
imposes: 10.8153832958
assume: 10.8153832958
backed: 10.8153832958
scream: 10.8153832958
switched: 11.8153832958
encourage: 11.8153832958
swap: 11.8153832958
relieve: 11.8153832958
seized: 11.8153832958
returning: 11.8153832958
infringed: 11.8153832958
battle: 11.8153832958
imply: 11.8153832958
revolves: 11.8153832958
prompts: 11.8153832958
expressed: 11.8153832958
endorse: 11.8153832958
delivering: 11.8153832958
issued: 11.8153832958
scrapped: 11.8153832958
obtained: 11.8153832958
defeat: 11.8153832958
composed: 11.8153832958
lengthen: 11.8153832958
decried: 11.8153832958
contains: 11.8153832958
planted: 11.8153832958
voted: 11.8153832958
brings: 11.8153832958
equipped: 11.8153832958
acceded: 11.8153832958
known: 11.8153832958
predict: 11.8153832958
arise: 11.8153832958
ensnarled: 11.8153832958
travel: 11.8153832958
scaring: 11.8153832958
blocks: 11.8153832958
flourish: 11.8153832958
profited: 11.8153832958
attempt: 11.8153832958
memorize: 11.8153832958
pointed: 11.8153832958
affect: 11.8153832958
negotiated: 11.8153832958
complicate: 11.8153832958
reaping: 11.8153832958
seeking: 11.8153832958
propose: 11.8153832958
complain: 11.8153832958
referred: 11.8153832958
stresses: 11.8153832958
aggravated: 11.8153832958
happen: 11.8153832958
emerged: 11.8153832958
swing: 11.8153832958
restructures: 11.8153832958
rang: 11.8153832958
inching: 11.8153832958
rooted: 11.8153832958
jet: 11.8153832958
indicate: 11.8153832958
attached: 11.8153832958
pushes: 11.8153832958
diminish: 11.8153832958
depressed: 11.8153832958
slowed: 11.8153832958
feeling: 11.8153832958
collecting: 11.8153832958
pursued: 11.8153832958
forces: 11.8153832958
harped: 11.8153832958
stayed: 11.8153832958
measures: 11.8153832958
reach: 11.8153832958
hamstrung: 11.8153832958
faint: 11.8153832958
expired: 11.8153832958
dissolves: 11.8153832958
upset: 11.8153832958
depended: 11.8153832958
finalized: 11.8153832958
unleashed: 11.8153832958
gains: 11.8153832958
banned: 11.8153832958
conduct: 11.8153832958
polarized: 11.8153832958
exists: 11.8153832958
depends: 11.8153832958
attempting: 11.8153832958
rings: 11.8153832958
targeted: 11.8153832958
approach: 11.8153832958
consists: 11.8153832958
exceeds: 11.8153832958
swallow: 11.8153832958
prepared: 11.8153832958
stretched: 11.8153832958
loaded: 11.8153832958
allocated: 11.8153832958
puts: 11.8153832958
AGREES: 11.8153832958
devise: 11.8153832958
describes: 11.8153832958
raced: 11.8153832958
assessed: 11.8153832958
seeks: 11.8153832958
loom: 11.8153832958
ripen: 11.8153832958
rigged: 11.8153832958
weighed: 11.8153832958
pressing: 11.8153832958
worry: 11.8153832958
touched: 11.8153832958
tells: 11.8153832958
capped: 11.8153832958
showing: 11.8153832958
hang: 11.8153832958
running: 11.8153832958
alleviate: 11.8153832958
hauled: 11.8153832958
speed: 11.8153832958
fled: 11.8153832958
confined: 11.8153832958
using: 11.8153832958
imposed: 11.8153832958
signal: 11.8153832958
discarded: 11.8153832958
improves: 11.8153832958
indicating: 11.8153832958
exposed: 11.8153832958
recorded: 11.8153832958
overlap: 11.8153832958
picks: 11.8153832958
refer: 11.8153832958
stem: 11.8153832958
exercised: 11.8153832958
adds: 11.8153832958
stoked: 11.8153832958
accommodate: 11.8153832958
contrasts: 11.8153832958
terminated: 11.8153832958
liquidated: 11.8153832958
knitted: 11.8153832958
faded: 11.8153832958
measure: 11.8153832958
moved: 11.8153832958
trimming: 11.8153832958
educated: 11.8153832958
aces: 11.8153832958
watched: 11.8153832958
moves: 11.8153832958
understands: 11.8153832958
forcing: 11.8153832958
conclude: 11.8153832958
's: 11.8153832958
refunded: 11.8153832958
searched: 11.8153832958
contends: 11.8153832958
booming: 11.8153832958
implies: 11.8153832958
expands: 11.8153832958
blinks: 11.8153832958
lasted: 11.8153832958
push: 11.8153832958
"""
