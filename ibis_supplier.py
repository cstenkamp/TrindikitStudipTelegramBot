import settings
import studip
import travel


if settings.MULTIUSER:
    import multiUser_ibis
else:
    import singleUser_ibis



def loadIBIS(forwhat, language):

    if forwhat == "studip":
        apiconnector = studip.create_studip_APIConnector()
        grammar = studip.create_studip_grammar(language)
        domain = studip.create_studip_domain(apiconnector)
    elif forwhat == "travel":
        apiconnector = travel.create_travel_APIConnector()
        grammar = travel.create_travel_grammar()
        domain = travel.create_travel_domain()


    if settings.MULTIUSER:
        ibis = multiUser_ibis.IBIS2(domain, apiconnector, grammar)
    else:
        ibis = singleUser_ibis.IBIS1(domain, apiconnector, grammar)
    return ibis



#####################################################################
# Running the dialogue system
######################################################################

if __name__=='__main__':
    if not settings.MULTIUSER:
        ibis = loadIBIS("travel", "en")
        ibis.init()
        ibis.control()
    else:
        print("Multiuser is on")