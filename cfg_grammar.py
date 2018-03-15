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
from myparser import MyParser
from copy import deepcopy
from trindikit import set

if settings.MULTIUSER:
    nltk.data.path.append("/var/www/")
    nltk.data.path.append("/var/www/nltk_data/")
else:
    nltk.data.path.append("/home/chris/nltk_data/")
    nltk.data.path.append("/home/chris/")


######################################################################
# CFG grammar based on NLTK
######################################################################

class NotRecognizedException(Exception):
    pass

class CFG_Grammar(Grammar):
    """CFG parser based on NLTK."""
    
    def loadGrammar(self, grammarFilename):
        preprocessed = self.preprocess_grammar(grammarFilename)
        self.neighbours = self.find_neighbours_of_variables()
        # self.parser = nltk.load_parser(grammarFilename, trace=1 if settings.VERBOSE["Parse"] else 0, cache=False) #nciht mehr parse.[...]
        # self.parser = nltk.parse.FeatureEarleyChartParser(nltk.grammar.FeatureGrammar.fromstring(preprocessed), trace=settings.VERBOSE["Parse"])
        self.parser = MyParser(nltk.grammar.FeatureGrammar.fromstring(preprocessed), trace=settings.VERBOSE["Parse"])


    def interpret(self, input, IS, DOMAIN, NEXT_MOVES, anyString=False, moves=None): #überschreibe ich nochmal in studip
        """Parse an input string into a dialogue move or a set of moves."""
        try: return self.parseString(input, IS, DOMAIN, NEXT_MOVES)
        except: pass
        try: return eval(input)
        except: pass
        if anyString:
            return Answer(ShortAns(input))
        return set([])


    def parseString(self, input, IS, DOMAIN, NEXT_MOVES):
        tokens = self.preprocess_input(input).split()
        try:
            trees = next(self.parser.parse(tokens))  # http://www.nltk.org/book/ch09.html
            root = trees[0].label()
        except:
            typstringlist = self.parser.partial_parse(tokens, self.neighbours) #TODO der partialparser muss besser sodass er ne einduetige antwort zurückgibt >.<
            for i, (typ, string) in enumerate(typstringlist):
                string2 = string.replace("_", " ").replace("?", "")
                # print("STRING", string)
                try:
                    converted = self.use_converters(IS, DOMAIN, string2, typ, NEXT_MOVES)
                    break
                except NotRecognizedException as e:
                    if i < len(typstringlist):
                        pass
                    else:
                        NEXT_MOVES.push(State("I did not recognize the " + typ + " you queried!"))
                        raise e
            # print("CONVERTED", converted)
            tokens = " ".join(tokens).replace(string, "{"+typ+"}").split(" ")
            # print("NEU ZU PARSEN:", tokens)
            trees = next(self.parser.parse(tokens))
            root = trees[0].label()
            root = deepcopy(dict(root))
            if root["sem"]["f"] == "given": root["sem"]["f"] = converted
            root["sem"]["fulfilltype"] = typ
        try:
            return self.sem2move(root['sem'], IS, DOMAIN, NEXT_MOVES)
        except:
            pass
        try:
            return self.type2move(root[list(dict(root).keys())[0]])  # geez.
        except:
            pass
        return ""


    def use_converters(self, IS, DOMAIN, string, answertype, NEXT_MOVES):
        try:
            auth_string = IS.shared.com.get("auth_string").content[1].content
            content = DOMAIN.converters[answertype](auth_string, string)
            if not content:
                raise NotRecognizedException
            return content
        except Exception as e: #wenn es noch keinen auth-string gibt versteht er das einfach nicht(!)
            raise NotRecognizedException


    def preprocess_input(self, input):
        input = input.lower()
        for tofind, replacewith in sorted(list(self.longstrings.items()), key=lambda item: len(item[1]), reverse=True):
            if tofind in input:
                input = input.replace(tofind, replacewith) #anders gehen keine leerzeichen in einem speech act
        return input


    def type2move(self, roottype):
        if roottype == "QUIT":
            return Quit()
        raise Exception


    def sem2move(self, sem, IS, DOMAIN, NEXT_MOVES):
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
            if settings.VERBOSE["Question"]:
                print("THE QUESTION WAS:\n"+str(sem))
            sem["Ask"]
            if sem["subtype"] == "YNQ":
                return Ask(YNQ(Prop(Pred0(sem["Ask"]))), askedby="USR")
            elif sem["subtype"] == "WHQ":
                return Ask(WhQ(Pred1(sem['Ask'])), askedby="USR")
            elif sem["subtype"] == "SecOrdQ":
                if not sem.get("f") or str(sem["f"]).startswith("?"):
                    return Ask(SecOrdQ(Pred2(sem['Ask'], DOMAIN)), askedby="USR")
                else:
                    range = DOMAIN.preds2[sem['Ask']] #range[1] ist die neue frage, range[0] der answer-typ
                    if sem.get("fulfilltype"): range = [i for i in range if i[0] == sem["fulfilltype"]]
                    content = self.use_converters(IS, DOMAIN, sem["f"], range[0][0], NEXT_MOVES)
                    return Ask(WhQ(Pred1(range[0][1], content, createdfrom=sem['Ask'])), askedby="USR")
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
        self.variables = {}
        self.variablepath = {}
        with open(grammarFilename, "r", encoding="utf-8") as f:
            lines = [line for line in f]
        for i in range(len(lines)):
            lines[i] = self.line_ops(lines[i], self.variablepath)
            lines[i] = self.incorporate_optionals(lines[i])
            lines[i] = self.find_longstrings(lines[i])
            #other line-operations here (on line)

        preprocessed = "\n".join(lines)
        #other overall operations here (on preprocessed)
        for key,val in self.longstrings.items():
            preprocessed = preprocessed.replace("'"+key+"'", "'"+val+"'")

        return preprocessed


    def find_neighbours_of_variables(self):
        tmp = [(v,k) for k, v in self.variablepath.items()]
        # for key,val in tmp:
        #     print(key, "->", val)
        # okay, hier muss man sich vorher und nachher tmp printen um zu gucken was passiert... tatsache ist, es wird geschaut
        # wovon die variablen benachbart sein können.
        whattoreplace = list(self.variables.items())
        while len(whattoreplace) > 0:
            innerkey, innerval = whattoreplace[0]
            for key, val in tmp:
                if val == innerkey:
                    tmp.append((key, innerval))
                    whattoreplace.append((key, innerval))
                elif " " in val:
                    reconstr = []
                    for i in val.split(" "):
                        reconstr.append(i if i != innerkey else innerval)
                    if " ".join(reconstr) != val:
                        tmp.append((key, " ".join(reconstr)))
                        whattoreplace.append((key, " ".join(reconstr)))
            del whattoreplace[0]
        # for key,val in tmp:
        #     print(key, "->", val)
        neighbours = set()
        for _, val in tmp:
            if " " in val:
                pos = val.split(" ")
                for i in range(len(pos)):
                    if pos[i] in self.variables.values():
                        if i>0:
                            neighbours.add((pos[i-1], "r", pos[i]))
                        if i<len(pos)-1:
                            neighbours.add((pos[i+1], "l", pos[i]))
        return list(neighbours)



    def rem_spaces(self, text):
        text = text.replace("\n", "")
        while text.startswith(" "):
            text = text[1:]
        while text.endswith(" "):
            text = text[:-1]
        return text


    def line_ops(self, line, variablepath):
        if not line.startswith('#') and "->" in line and "'" in line: #terminals
            strings = re.findall("-> ?'(.*?)'", line) + re.findall("\| ?'(.*?)'", line)
            for curr in strings:
                line = line.replace("'"+curr+"'", "'"+curr.lower()+"'")
                tmp = self.find_variables(curr, line, self.variables)
                if tmp: self.variablepath[self.rem_spaces(tmp[1])] = self.rem_spaces(tmp[0])
                # other string-operations here (on strings, an array)
        elif not line.startswith('#') and "->" in line: #non-terminals:
            # print(line)
            l = re.sub("\[.*?\]", "", line).replace("[", "").replace("]", "")
            rightpart = l[l.find("->")+2:]
            while rightpart.find("|") > 0:
                variablepath[self.rem_spaces(rightpart[:rightpart.find("|")-1])] = self.rem_spaces(l[:l.find("->")])
                rightpart = rightpart[rightpart.find("|")+1:]
            variablepath[self.rem_spaces(rightpart)] = self.rem_spaces(l[:l.find("->")])
        return line




    def find_variables(self, string, line, appendto):
        if "{" in string and "}" in string:
            var = re.findall("\{(.*?)\}", string)[0]
            otherside = re.sub("\[.*?\]", "", line[:line.find("->")])
            newline = otherside, "'{"+var+"}'"
            appendto[self.rem_spaces(otherside)] = "'{"+var+"}'"
            return newline
        return False


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
