import nltk.parse
import re
import numpy as np

class MyParser(nltk.parse.FeatureEarleyChartParser):

    def partial_parse(self, tokens, neighbours):
        trace = self._trace
        trace_new_edges = self._trace_new_edges

        tokens = list(tokens)
        # self._grammar.check_coverage(tokens)
        chart = self._chart_class(tokens)
        grammar = self._grammar

        # Width, for printing trace edges.
        trace_edge_width = self._trace_chart_width // (chart.num_leaves() + 1)
        if trace: print(chart.pretty_format_leaves(trace_edge_width))

        for axiom in self._axioms:
            new_edges = list(axiom.apply(chart, grammar))
            trace_new_edges(chart, axiom, new_edges, trace, trace_edge_width)

        possibilities = []

        inference_rules = self._inference_rules
        for end in range(chart.num_leaves()+1):
            if trace > 1: print("\n* Processing queue:", end, "\n")
            agenda = list(chart.select(end=end))
            while agenda:
                edge = agenda.pop()
                possibilities.append(str(edge))
                for rule in inference_rules:
                    new_edges = list(rule.apply(chart, grammar, edge))
                    trace_new_edges(chart, rule, new_edges, trace, trace_edge_width)
                    for new_edge in new_edges:
                        if new_edge.end()==end:
                            agenda.append(new_edge)

        constituents = []
        terminals = []
        for i in possibilities:
            if int(i[3])-int(i[1]) and i[6] != "'":
                # print(i[:i.find("->")])
                constituents.append(i[:5]+re.sub("\[.*?\]", "", i[:i.find("->")]).replace("[", "").replace("]", ""))
            elif int(i[3])-int(i[1]) and i[6] == "'":
                terminals.append(i)

        tcopy = []
        for i in terminals:
            if not any(i[:5] == j[:5] for j in constituents):
                tcopy.append(i)
        terminals = tcopy

        terminals = merge_terminals(terminals)
        # print("\n".join(constituents))
        # print("\n".join(terminals))

        for i in constituents:
            tmp = rem_spaces(i[6:])
            for j in neighbours:
                if tmp == j[0]:
                    # print(i[:5], j)
                    if j[1] == "r":
                        for k in terminals:
                            if i[3] == k[1]:
                                # print("THIS ONE NEEDS TO BE", j[2][2:-2], ":", re.findall("\'(.*?)\'", k)[0])
                                return j[2][2:-2], k[k.find("'")+1:-1]
                    elif j[1] == "l":
                        for k in terminals:
                            if i[1] == k[3]:
                                # print("THIS ONE NEEDS TO BE", j[2][2:-2], ":", re.findall("\'(.*?)\'", k)[0])
                                return j[2][2:-2], k[k.find("'") + 1:-1]

        return None, None


def rem_spaces(text):
    text = text.replace("\n", "")
    while text.startswith(" "):
        text = text[1:]
    while text.endswith(" "):
        text = text[:-1]
    return text




def merge_terminals(terminals):
    if len(terminals) > 1:  # wenn es was von [1:2] und [2:3] gibt, merge diese zu einem [1:3]
        for _ in range(100):
            for i in range(len(terminals) - 1):
                for j in range(len(terminals) - i):
                    if terminals[i][3] == terminals[i + j][1]:
                        tmp = "[" + terminals[i][1] + ":" + terminals[i + j][3] + "] '" + rem_spaces(
                            terminals[i][6:].replace("'", "")) + " " + rem_spaces(terminals[i + j][6:].replace("'", "") + "'")
                        if tmp not in terminals:
                            terminals.append(tmp)
        tcopy = []
        startindices = sorted(list(set(i[1] for i in terminals)))
        for i in startindices:
            mx = max([(j, int(j[3])) for j in terminals if j[1] == i], key=lambda p: p[1])
            # print(i, "max:", mx[0])
            tcopy.append(mx[0])

        terminals = set()
        for i in range(len(tcopy)):
            cando = True
            for j in range(len(tcopy)):
                if j == i: continue
                first = range(int(tcopy[i][1]), int(tcopy[i][3]))
                secnd = range(int(tcopy[j][1]), int(tcopy[j][3]))
                if set(first) <= set(secnd):
                    cando = False
            if cando: terminals.add(tcopy[i])
    return list(terminals)
