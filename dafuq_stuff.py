from nltk import load_parser
from ibis_types import Answer, Ask, WhQ, Pred1, Question, Ans, Quit

VERBOSE = {"Parse": True}


class Grammar(object):
    """The simplest grammar, using dialogue moves as surface strings.

    Override generate and interpret if you want to use a real grammar.
    """

    def generate(self, moves):
        """Generate a surface string from a set of dialogue moves."""
        return self.joinPhrases(self.generateMove(move) for move in moves)

    def generateMove(self, move):
        return str(move)

    def joinPhrases(self, phrases):
        str = ""
        for p in phrases:
            if str != "": str += " "
            str += p
            if not (p[-1] == "." or p[-1] == "?" or p[-1] == "!"):
                str += "."
        return str

    def interpret(self, input):
        """Parse an input string into a dialogue move or a set of moves."""
        try:
            return eval(input)
        except Exception as e:
            print("line 34", e)
        try:
            return Ask(Question(input))
        except  Exception as e:
            print("line 38", e)
        try:
            return Answer(Ans(input))
        except Exception as e:
            print("line 42", e)
        return None

class CFG_Grammar(Grammar):
    """CFG parser based on NLTK."""

    def loadGrammar(self, grammarFilename):
        self.parser = load_parser(grammarFilename, trace=1 if VERBOSE["Parse"] else 0,
                                  cache=False)  # nciht mehr parse.[...]

    def interpret(self, input):
        """Parse an input string into a dialogue move or a set of moves."""
        return self.parseString(input)
        try:
            pass
        except Exception as e:
            print("line 58", e)
        try:
            return eval(input)
        except Exception as e:
            print("line 62", e)
        return set([])

    def parseString(self, input):
        print("INPUT", input)
        tokens = input.split()
        trees = next(self.parser.parse(tokens))
        print("### LABEL ###")
        print(trees[0].label())
        print("### LABEL END ###")
        root = trees[0].label()
        try:
            return self.sem2move(root['sem'])
        except:
            return self.type2move(root[list(dict(root).keys())[0]]) #geez.

    def type2move(self, roottype):
        if roottype == "QUIT":
            return Quit()

    def sem2move(self, sem):
        try:
            return Answer(sem['Answer'])
        except Exception as e:
            print("line 79", e)
        try:
            ans = sem['Answer']
            pred = ans['pred']
            ind = ans['ind']
            # return Answer(Prop((Pred1(pred, Ind(ind), True))))
            return Answer(pred + "(" + ind + ")")
        except Exception as e:
            print("line 87", e)
        try:
            return Ask(WhQ(Pred1(sem['Ask'])))
        except Exception as e:
            print("line 91", e)
        try:
            return Quit()
        except Exception as e:
            print("line 99", e)
        raise Exception


g = CFG_Grammar()
g.loadGrammar("file:travel.fcfg")
print("RESULT", g.interpret("bye"))