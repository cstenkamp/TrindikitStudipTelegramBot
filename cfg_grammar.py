# -*- encoding: utf-8 -*-

#
# cfg_grammar.py
# Copyright (C) 2009, Alexander Berman. All rights reserved.
#

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published 
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# and the GNU Lesser General Public License along with this program.  
# If not, see <http://www.gnu.org/licenses/>.

from ibis_types import Answer, Ask, WhQ, Pred1, Quit, YNQ, Prop, Pred0
from nltk import load_parser #parse ist deprecated, https://stackoverflow.com/questions/31308497/attributeerror-featurechartparser-object-has-no-attribute-nbest-parse
from ibis import Grammar
from trindikit import VERBOSE

######################################################################
# CFG grammar based on NLTK
######################################################################

class CFG_Grammar(Grammar):
    """CFG parser based on NLTK."""
    
    def loadGrammar(self, grammarFilename):
        self.parser = load_parser(grammarFilename, trace=1 if VERBOSE["Parse"] else 0, cache=False) #nciht mehr parse.[...]

    def interpret(self, input):
        """Parse an input string into a dialogue move or a set of moves."""
        try: return self.parseString(input)
        except: pass
        try: return eval(input)
        except: pass
        return set([])

    def parseString(self, input):
        tokens = input.split()
        trees = next(self.parser.parse(tokens))
        root = trees[0].label()
        try:
            return self.sem2move(root['sem'])
        except:
            return self.type2move(root[list(dict(root).keys())[0]]) #geez.

    def type2move(self, roottype):
        if roottype == "QUIT":
            return Quit()

    def sem2move(self, sem):
        #sem bspw: [Ask = 'needvisa'] [ subtype = 'YNQ']
        try: return Answer(sem['Answer'])
        except: pass
        try:
            ans = sem['Answer']
            pred = ans['pred']
            ind = ans['ind']
            #return Answer(Prop((Pred1(pred, Ind(ind), True))))
            return Answer(pred+"("+ind+")")
        except: pass
        try:
            sem["Ask"]
            if sem["subtype"] == "YNQ":
                return Ask(YNQ(Prop(Pred0(sem["Ask"]))))
            elif sem["subtype"] == "WHQ":
                return Ask(WhQ(Pred1(sem['Ask'])))
        except:
            pass
        raise Exception

