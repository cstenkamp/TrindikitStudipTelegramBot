from nltk import load_parser



class CFG_Grammar():
    """CFG parser based on NLTK."""

    def loadGrammar(self, grammarFilename):
        self.parser = load_parser(grammarFilename, trace=1, cache=False)

    def parseString(self, input):
        tokens = input.split()
        trees = next(self.parser.parse(tokens))
        print("TREES", trees)
        lab = trees[0].label()
        print("LABEL", lab[list(dict(lab).keys())[0]])


g = CFG_Grammar()
g.loadGrammar("file:travel.fcfg")
print("RESULT", g.parseString("yes"))