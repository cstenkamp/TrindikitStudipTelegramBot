from ibis_rules import *
from more_itertools import peekable
import singleUser_ibis
import os

import studip
import travel

######################################################################
# Overwritten classes - DM must contain the generator, and the IO must be replaced
######################################################################

class IBISController(DialogueManager):
    def IO(self):
        """The IBIS control algorithm."""
        if not self.IS.private.plan:
            self.IS.private.agenda.push(Greet())
        self.print_state()
        output = True
        while output:
            output = []
            self.select()  # puts the next appropriate thing onto the agenda
            while self.NEXT_MOVES:
                self.generate()  # sets output
                output.append(self.output(None))
                self.update()  # integrates answers, ..., loads & executes plan
                self.print_state()

            if self.PROGRAM_STATE.get() == ProgramState.QUIT:
                break

            if output:
                input = yield(output)
                if input:
                    if input.startswith("U> "): input = input[3:]
                    self.INPUT.set(input)
                    self.LATEST_SPEAKER.set(Speaker.USR)

            res = self.interpret()  # obviously also runs it
            if res == "exit":
                break

            self.update()
            self.print_state()



class DebugOutput(SimpleOutput):
    @update_rule
    def output(NEXT_MOVES, OUTPUT, LATEST_SPEAKER, LATEST_MOVES):
        """Print the string in OUTPUT to standard output.

        After printing, the set of NEXT_MOVES is moved to LATEST_MOVES,
        and LATEST_SPEAKER is set to SYS.
        """
        res = "S: "+(str(OUTPUT.get()) or "[---]")
        LATEST_SPEAKER.set(Speaker.SYS)
        LATEST_MOVES.clear()
        if settings.MERGE_SUBSQ_MESSAGES:
            LATEST_MOVES.update(NEXT_MOVES)
            NEXT_MOVES.clear()
        else:
            LATEST_MOVES.update([NEXT_MOVES.elements[0]])
            del NEXT_MOVES.elements[0]
        return res



#alles genauso wie das IBIS, aber überschreibe Output mit DebugOutput und diesem DialogueManager, der IO hat
class IBIS(DebugOutput, singleUser_ibis.IBIS, IBISController, singleUser_ibis.IBISInfostate, StandardMIVS,  SimpleInput,    DialogueManager):
    pass


class IBIS3(IBIS, singleUser_ibis.IBIS1): #inherit the rule_groups and the update-loop from singeUser.IBIS1
    pass



########################################################################################################################
########################################################################################################################
####################################################### main ###########################################################
########################################################################################################################
########################################################################################################################


def loadIBIS(forwhat, language):

    if forwhat == "studip":
        apiconnector = studip.create_studip_APIConnector()
        grammar = studip.create_studip_grammar(language)
        domain = studip.create_studip_domain(apiconnector)
    elif forwhat == "travel":
        apiconnector = travel.create_travel_APIConnector()
        grammar = travel.create_travel_grammar()
        domain = travel.create_travel_domain()

    ibis = IBIS3(domain, apiconnector, grammar)
    return ibis



# def test_answer():
#     assert func(3) == 5


def check_sentence(ibis, sentence):
    parts = sentence.split("\n")
    parts2 = []
    parts3 = []
    for i in parts:
        if any(j.isalnum() for j in i):
            while i[0] == " ": i = i[1:]
            while i[-1] == " ": i = i[:-1]
            parts2.append(i)
    tmpstring = ""
    for i in parts2:
        if i.startswith("S: ") or i.startswith("U> "):
            if len(tmpstring) > 0: parts3.append(tmpstring[:-1])
            tmpstring = ""
        tmpstring += i+"\n"
    if len(tmpstring) > 0: parts3.append(tmpstring[:-1])

    sentence_iterator = peekable(iter([None] + parts3)) #erst die beiden in ne list, dann daraus nen iter, daraus peekable

    generator = ibis.IO()
    for nextSentence in sentence_iterator:
        if nextSentence is None or nextSentence.startswith("U> "):
            syssent = generator.send(nextSentence)
            syssent_iter = iter(syssent)
            try:
                while sentence_iterator.peek().startswith("S: "):
                    next_system_sent = remove_spaces(next(syssent_iter))
                    nextSentence = next(sentence_iterator)
                    try:
                        tmp = list(nextSentence)
                        for i in range(len(nextSentence)):
                            if tmp[i] == "#":
                                tmp[i] = next_system_sent[i]
                        nextSentence = "".join(tmp)
                        assert nextSentence == next_system_sent
                    except AssertionError as e:
                        print("------------------------------", file=sys.stderr)
                        print("SHOULD BE:", nextSentence, file=sys.stderr)
                        print("-", file=sys.stderr)
                        print("IS:", next_system_sent, file=sys.stderr)
                        print("------------------------------", file=sys.stderr)
                        raise e
            except StopIteration:
                continue

def remove_spaces(text):
    res = []
    for i in text.split("\n"):
        while i[0] == " ": i = i[1:]
        while i[-1] == " ": i = i[:-1]
        res.append(i)
    return "\n".join(res)


def check_commands():
    for dom in ["travel", "studip"]:
        for lan in ["en", "de"]:
            print("------ testing "+dom+" in "+lan+" ------")
            ibis = loadIBIS(dom, lan)
            ibis.init()

            filename = os.path.join(settings.PATH, "test_strings/", dom+"_"+lan)
            if os.path.exists(filename):
                for i in collect_string(filename):
                    if i == "<restart>":
                        ibis = loadIBIS(dom, lan)
                        ibis.init()
                    else:
                        yield ibis, i
            return #TODO REMOVE ME


def collect_string(filename):
    with open(filename, "r") as file:
        tmp = ""
        firsttime = True
        for i in file:
            if i.startswith("---"):
                yield tmp
                tmp = ""
                firsttime = False
            elif i.startswith("<restart>"):
                return "<restart>"
            else:
                if firsttime or (not firsttime and i != "S: Hello.\n"):
                    tmp += i
        yield tmp


def sent_short(sent):
    spl = sent.split("\n")
    if spl[0] == "S: Hello.":
        return spl[1]
    return spl[0]


if __name__=='__main__':
    fail_count = 0
    ges_count = 0
    for ibis, sent in check_commands():
        try:
            check_sentence(ibis, sent)
        except AssertionError:
            print("The following sentence sucked:", sent_short(sent))
            fail_count += 1
        else:
            print("The following sentence worked:", sent_short(sent))
        ges_count += 1

    print("Amount of errors:"+str(fail_count)+"/"+str(ges_count))

    #TODO mit dem "Was kannst du?"-commando die tests selbst auf completeness prüfen



########################################################################################################################
############################################ for pytest, not running ###################################################
########################################################################################################################


def test_travel_en():
    ibis = loadIBIS("travel", "en")
    ibis.init()

    filename = os.path.join(settings.PATH, "test_strings/travel_en")
    if os.path.exists(filename):
        for i in collect_string(filename):
            if i == "<restart>":
                ibis = loadIBIS("travel", "en")
                ibis.init()
            else:
                check_sentence(ibis, i)



def test_studip_en():
    ibis = loadIBIS("travel", "en")
    ibis.init()

    filename = os.path.join(settings.PATH, "test_strings/travel_en")
    if os.path.exists(filename):
        for i in collect_string(filename):
            if i == "<restart>":
                ibis = loadIBIS("travel", "en")
                ibis.init()
            else:
                check_sentence(ibis, i)