# -*- encoding: utf-8 -*-

#
# travel.py
#
# The author or authors of this code dedicate any and all 
# copyright interest in this code to the public domain.


from ibis import *
from cfg_grammar import *
from ibis_types import Findout, If, ConsultDB, Ind


def create_domain():
    preds0 = 'return', 'need-visa'

    preds1 = {'price': 'int',
              'how': 'means',
              'dest_city': 'city',
              'depart_city': 'city',
              'depart_day': 'day',
              'class': 'flight_class',
              'return_day': 'day',
              }

    means = 'plane', 'train'
    cities = 'paris', 'london', 'berlin'
    days = 'today', 'tomorrow'
    classes = 'first', 'second'

    sorts = {'means': means,
             'city': cities,
             'day': days,
             'flight_class': classes,
             }

    domain = Domain(preds0, preds1, sorts)

    domain.add_plan("?x.price(x)",
                   [Findout("?x.how(x)"),
                    Findout("?x.dest_city(x)"),
                    Findout("?x.depart_city(x)"),
                    Findout("?x.depart_day(x)"),
                    Findout("?x.class(x)"),
                    Findout("?return()"),
                    If("?return()",
                        [Findout("?x.return_day(x)")]),
                    ConsultDB("?x.price(x)")
                   ])

    return domain


class TravelDB(Database):

    def __init__(self):
        self.entries = []

    def consultDB(self, question, context):
        depart_city = self.getContext(context, "depart_city")
        dest_city = self.getContext(context, "dest_city")
        day = self.getContext(context, "depart_day")
        do_return = self.getContext(context, "return")
        entry = self.lookupEntry(depart_city, dest_city, day, do_return)
        price = entry['price']
        return Prop(Pred1("price"), Ind(price), True)

    def lookupEntry(self, depart_city, dest_city, day, do_return):
        for e in self.entries:
            if e['from'] == depart_city and e['to'] == dest_city and e['day'] == day and e['return'] == do_return:
                return e
        assert False

    def getContext(self, context, pred):
        for prop in context:
            if prop.pred.content == pred:
                try:
                    return prop.ind.content
                except AttributeError: #NoneType
                    return prop.yes #bei Yes-No-Questions
        assert False

    def addEntry(self, entry):
        self.entries.append(entry)


class TravelGrammar(SimpleGenGrammar, CFG_Grammar):
    def generateMove(self, move):
        try:
            assert isinstance(move, Answer)
            prop = move.content
            assert isinstance(prop, Prop)
            assert prop.pred.content == "price"
            return "The price is " + str(prop.ind.content)
        except:
            return super(TravelGrammar, self).generateMove(move)


def loadIBIS():
    grammar = TravelGrammar()
    grammar.loadGrammar("file:travel.fcfg")
    grammar.addForm("Ask('?x.how(x)')", "How do you want to travel?")
    grammar.addForm("Ask('?x.dest_city(x)')", "Where do you want to go?")
    grammar.addForm("Ask('?x.depart_city(x)')", "From where are you leaving?")
    grammar.addForm("Ask('?x.depart_day(x)')", "When do you want to leave?")
    grammar.addForm("Ask('?x.return_day(x)')", "When do you want to return?")
    grammar.addForm("Ask('?x.class(x)')", "First or second class?")
    grammar.addForm("Ask('?return()')", "Do you want a return ticket?")

    database = TravelDB()
    database.addEntry({'price': '232', 'from': 'berlin', 'to': 'paris', 'day': 'today', 'return': False})
    database.addEntry({'price': '345', 'from': 'paris', 'to': 'london', 'day': 'today', 'return': False})
    database.addEntry({'price': '432', 'from': 'berlin', 'to': 'paris', 'day': 'today', 'return': True})

    domain = create_domain()

    ibis = IBIS1(domain, database, grammar)
    return ibis



# Följande måste klaras av såsmåningom:
#
# contact_plan(change_contact_name, change, contact,
# 	     [],
# 	     [ findout(C^change_contact_new_name(C),
# 		       { type=text, default=change_contact_name, device=phone }),
# 	       dev_do(phone, 'ChangeContactName'),
# 	       forget(view_contact_name(_)),
# 	       forget(change_contact_name(_)),
# 	       if_then(change_contact_new_name(Name),
# 		       [ assume_shared(view_contact_name(Name)),
# 			 assume_shared(change_contact_name(Name)) ]),
# 	       forget(change_contact_new_name(_))
# 	     ]).
# postcond(change_contact_name, done('ChangeContactName')).
#
# OBS! if_then(..) binder en variabel Name som används i konsekvensen!
# Förslag:
#
#    If("change-contact-name(?x)", [assume_shared("view-contact-name(?x)"), ...])


######################################################################
# Running the dialogue system
######################################################################

if __name__=='__main__':
    ibis = loadIBIS()
    ibis.run()

    # ibis.init()
    # if not ibis.IS.private.plan:
    #     ibis.IS.private.agenda.push(Greet())
    #
    # while True:
    #     ibis.select()  # puts the next appropriate thing onto the agenda (->what is the differnce here between NEXT_MOVES und der agenda?)
    #     if ibis.NEXT_MOVES:
    #         ibis.generate()  # sets output
    #         ibis.output()  # prints output
    #         ibis.update()  # integrates answers, ..., loads & executes plan
    #     if ibis.PROGRAM_STATE.get() == ProgramState.QUIT:
    #         break
    #     ibis.input()
    #     # if ibis.interpret() == "exit":  # obviously also runs it
    #     #     break
    #     ibis.update()
