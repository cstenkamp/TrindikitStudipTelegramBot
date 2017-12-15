from ibis import Grammar
from ibis_types import Answer, Ask, WhQ, Pred1
from nltk import load_parser #parse ist deprecated, https://stackoverflow.com/questions/31308497/attributeerror-featurechartparser-object-has-no-attribute-nbest-parse

####################### such that basestring can be used ######################
try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str,bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring
####################### such that basestring can be used ######################

######################################################################
# CFG grammar based on NLTK
######################################################################

class CFG_Grammar(Grammar):
    """CFG parser based on NLTK."""
    
    def loadGrammar(self, grammarFilename):
        self.parser = load_parser(grammarFilename, trace=1, cache=False) #nciht mehr parse.[...]

    def interpret(self, input):
        """Parse an input string into a dialogue move or a set of moves."""
        try: return self.parseString(input)
        except: pass
        try: return eval(input)
        except: pass
        return set([])

    def parseString(self, input):
        tokens = input.split()
#        trees = self.parser.nbest_parse(tokens) #ist jetzt ein Iterator!
#        sem = trees[0].node['sem'] #...der auch anders funktioniert >.<
        trees = next(self.parser.parse(tokens))
        sem = trees[0].label()['sem']        
        return self.sem2move(sem) 


    def sem2move(self, sem):
        try: return Answer(sem['Answer'])
        except: pass
        try:
            ans = sem['Answer']
            pred = ans['pred']
            ind = ans['ind']
            #return Answer(Prop((Pred1(pred, Ind(ind), True))))
            return Answer(pred+"("+ind+")")
        except: pass
        try: return Ask(WhQ(Pred1(sem['Ask'])))
        except: pass
        return None

