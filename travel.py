import os
import settings
from cfg_grammar import *
from ibis_types import Findout, If, ConsultDB, Ind
import trindikit
import ibis_generals

if settings.MULTIUSER:
    import multiUser_ibis
    PATH = "/var/www/studIPBot"
else:
    PATH = "/home/chris/Documents/UNI/sem_9/dialog_systems/Projekt/My_Trindikit/"
    import singleUser_ibis


########################################################################################################################
######################################################## DOMAIN ########################################################
########################################################################################################################

def create_travel_domain():
    preds0 = 'return', 'needvisa'
    # TODO - warum ist "return" ein zero-order-predicate? Dann ist es ja schon fulfilled - 0-order-predicates are propositions, aka sentences.
    # TODO - you can see the difference in the plan even: Findout(WhQ(Pred1('class'))), Findout(YNQ(Prop((Pred0('return'), None, True))))
    # TODO - The YNQ does already has the answer, and is thus a Proposition, and YNQs can be converted from that. Why is such a thing not a 1-place-predicate of the domain Boolean?
    # --- main ding das mich stört: warum ist es YNQ(Prop((Pred0('return'), None, True))) und nicht YNQ(Pred0('return')) --> warum muss es nochmal in ner Prop sein wo noch Truth-value bei ist

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
    days = 'today', 'tomorrow', 'monday', 'tuesday','wednesday','thursday','friday','saturday','sunday'
    classes = 'first', 'second'

    sorts = {'means': means,
             'city': cities,
             'day': days,
             'flight_class': classes,
             }

    domain = ibis_generals.Domain(preds0, preds1, None, sorts, None)

    ######################################### originaler fluginformation-kack ##########################################

    domain.add_plan("?x.price(x)",
                   [Findout("?x.how(x)"),
                    Findout("?x.dest_city(x)"),
                    Findout("?x.depart_city(x)"),
                    Findout("?x.depart_day(x)"),
                    Findout("?x.class(x)"),
                    Findout("?return()"),
                    If("?return()",
                        [Findout("?x.return_day(x)")]),
                    ConsultDB("?x.price(x)")  #das was precond der update-rule ist, nicht die funktion von unten!
                   ])

    domain.add_plan("?needvisa()",
                   [Findout("?x.dest_city(x)")
                    ])


    return domain


########################################################################################################################
#################################################### API_CONNECTOR #####################################################
########################################################################################################################


class TravelDB(ibis_generals.Database):

    def __init__(self):
        self.entries = []

    def consultDB(self, question, context, contextStr=""):
        depart_city = self.getContext(context, "depart_city", contextStr)[1].content
        dest_city = self.getContext(context, "dest_city", contextStr)[1].content
        day = self.getContext(context, "depart_day", contextStr)[1].content
        do_return = self.getContext(context, "return", contextStr)[1].content
        entry = self.lookupEntry(depart_city, dest_city, day, do_return)
        price = entry['price']
        return Prop(Pred1("price"), Ind(price), True)

    def lookupEntry(self, depart_city, dest_city, day, do_return):
        for e in self.entries:
            if e['from'] == depart_city and e['to'] == dest_city and e['day'] == day and e['return'] == do_return:
                return e
        assert False

    def addEntry(self, entry):
        self.entries.append(entry)


def create_travel_APIConnector():
    database = TravelDB()
    database.addEntry({'price': '232', 'from': 'berlin', 'to': 'paris', 'day': 'today', 'return': False})
    database.addEntry({'price': '345', 'from': 'paris', 'to': 'london', 'day': 'today', 'return': False})
    database.addEntry({'price': '432', 'from': 'berlin', 'to': 'paris', 'day': 'today', 'return': True})
    return database


########################################################################################################################
######################################################## GRAMMAR #######################################################
########################################################################################################################



class TravelGrammar(ibis_generals.SimpleGenGrammar, CFG_Grammar):
    def generateMove(self, move):
        try:
            assert isinstance(move, Answer)
            prop = move.content
            assert isinstance(prop, Prop)
            assert prop.pred.content == "price"
            return "The price is " + str(prop.ind.content)
        except:
            return super(TravelGrammar, self).generateMove(move)


def create_travel_grammar(lan="en"):
    grammar = TravelGrammar()
    grammar.loadGrammar(os.path.join(PATH,"grammars","travel"+"_"+lan+".fcfg"))
    if lan == "en":
        grammar.addForm("Ask('?x.how(x)')", "How do you want to travel?")
        grammar.addForm("Ask('?x.dest_city(x)')", "Where do you want to go?")
        grammar.addForm("Ask('?x.depart_city(x)')", "From where are you leaving?")
        grammar.addForm("Ask('?x.depart_day(x)')", "When do you want to leave?")
        grammar.addForm("Ask('?x.return_day(x)')", "When do you want to return?")
        grammar.addForm("Ask('?x.class(x)')", "First or second class?")
        grammar.addForm("Ask('?return()')", "Do you want a return ticket?")
    return grammar



########################################################################################################################
########################################################################################################################
########################################################################################################################


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

