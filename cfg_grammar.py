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

from ibis_types import * #Answer, Ask, WhQ, Pred1, Quit, YNQ, Prop, Pred0, Command, Imperative, ShortAns
import nltk  #parse ist deprecated, https://stackoverflow.com/questions/31308497/attributeerror-featurechartparser-object-has-no-attribute-nbest-parse
from ibis_generals import Grammar
import settings
import re

if settings.MULTIUSER:
    nltk.data.path.append("/var/www/")
    nltk.data.path.append("/var/www/nltk_data/")
else:
    nltk.data.path.append("/home/chris/nltk_data/")
    nltk.data.path.append("/home/chris/")


######################################################################
# CFG grammar based on NLTK
######################################################################

class CFG_Grammar(Grammar):
    """CFG parser based on NLTK."""
    
    def loadGrammar(self, grammarFilename):
        preprocessed = self.preprocess_grammar(grammarFilename)
        # self.parser = nltk.load_parser(grammarFilename, trace=1 if settings.VERBOSE["Parse"] else 0, cache=False) #nciht mehr parse.[...]
        self.parser = nltk.parse.FeatureEarleyChartParser(nltk.grammar.FeatureGrammar.fromstring(preprocessed), trace=1 if settings.VERBOSE["Parse"] else 0)


    def interpret(self, input, DOMAIN, anyString=False, moves=None, IS=None): #überschreibe ich nochmal in studip
        """Parse an input string into a dialogue move or a set of moves."""
        try: return self.parseString(input, DOMAIN)
        except: pass
        try: return eval(input)
        except: pass
        if anyString:
            return Answer(ShortAns(input))
        return set([])


    def parseString(self, input, DOMAIN):
        tokens = self.preprocess_input(input).split()
        trees = next(self.parser.parse(tokens))
        root = trees[0].label()
        try:
            return self.sem2move(root['sem'], DOMAIN)
        except:
            pass
        try:
            return self.type2move(root[list(dict(root).keys())[0]])  # geez.
        except:
            pass
        return ""


    def preprocess_input(self, input):
        input = input.lower()
        for tofind, replacewith in self.longstrings.items():
            if tofind in input:
                input = input.replace(tofind, replacewith) #anders gehen keine leerzeichen in einem speech act
        return input


    def type2move(self, roottype):
        if roottype == "QUIT":
            return Quit()
        raise Exception


    def sem2move(self, sem, DOMAIN):
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
            elif sem["subtype"] == "SecOrdQ":
                return Ask(SecOrdQ(Pred2(sem['Ask'], DOMAIN)))
        except:
            pass
        try:
            cmd = sem["Command"]
            if not cmd.startswith("!("):
                cmd = "!("+cmd+")"
            return Imperative(Command(cmd))
        except:
            pass

        raise Exception

    ####################################################################################################################
    ############################################# preprocessing stuff ##################################################
    ####################################################################################################################

    def preprocess_grammar(self, grammarFilename):
        preprocessed = ''
        self.longstrings = {}
        with open(grammarFilename, "r") as f:
            lines = [line for line in f]
        for i in range(len(lines)):
            lines[i] = self.line_ops(lines[i])
            lines[i] = self.incorporate_optionals(lines[i])
            lines[i] = self.find_longstrings(lines[i])
            #other line-operations here (on line)

        preprocessed = "\n".join(lines)
        #other overall operations here (on preprocessed)
        for key,val in self.longstrings.items():
            preprocessed = preprocessed.replace(key, val)
        return preprocessed


    def line_ops(self, line):
        if not line.startswith('#') and "->" in line and "'" in line:
            strings = re.findall("-> ?'(.*?)'", line) + re.findall("\| ?'(.*?)'", line)
            for curr in strings:
                line = line.replace("'"+curr+"'", "'"+curr.lower()+"'")
                # other string-operations here (on strings, an array)
        return line


    def incorporate_optionals(self, line):
        if not line.startswith('#') and "->" in line and "'" in line:
            strings = re.findall("-> ?'(.*?)'", line) + re.findall("\| ?'(.*?)'", line)
            newstrings = []
            for curr in strings:
                optionals = re.findall(r"\[[a-zA-Z]+?\]", curr)
                curr = re.sub(r"\[([a-zA-Z]+?)\]", r"[*]", curr)
                if len(optionals) > 0:
                    i = 0
                    while "[*]" in curr:
                        curr = curr.replace("[*]", "[" + str(i) + "]", 1)
                        i += 1

                    for i in range(2 ** len(optionals)):
                        formatstr = "0" * (len(optionals) - len("{0:b}".format(i))) + "{0:b}".format(
                            i)  # for eg 3 optionals its all combis from 000 -> 111
                        newone = curr
                        for i, kommtvor in enumerate(formatstr):
                            if kommtvor == "1":
                                newone = newone.replace("[" + str(i) + "]", optionals[i][1:-1])
                            else:
                                newone = newone.replace(" [" + str(i) + "]", "")
                        newstrings.append(newone)
                else:
                    newstrings.append(curr)
            newstrings = list(map(lambda x: "'" + x + "'", newstrings))
            newline = line[:line.index("->")] + "-> " + " | ".join(newstrings)
        else:
            newline = line
        return newline


    def find_longstrings(self, line):
        if not line.startswith('#') and "->" in line and "'" in line:
            strings = re.findall("-> ?'(.*?)'", line) + re.findall("\| ?'(.*?)'", line)
            self.longstrings = {**self.longstrings, **{i: i.replace(" ", "_") for i in strings if " " in i}}
            # longerstrings.extend([i for i in strings if " " in i])
        return line
