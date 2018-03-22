import ibis_generals


class StudIP_gen_grammar(ibis_generals.SimpleGenGrammar):
    def addForms(self):
        self.addForm("Answer(YesNo(False))", "DEUTSCH No.")
        self.addForm("Answer(YesNo(True))", "DEUTSCH Yes.")

        self.addForm("Ask('?x.username(x)')", "DEUTSCH Before we start, I need to know your username. What is it?")
        self.addForm("Ask('?x.password(x)')", "DEUTSCH Next up, your password please.")
        self.addForm("State('wtf')", "DEUTSCH Uhm, wtf")
        self.addForm("Ask('?x.coursename(x)')", "DEUTSCH From which course do you want to download?")
        self.addForm("Ask('?x.filename(x)')", "DEUTSCH Which file from that course do you want to download?")
        self.addForm("Ask('?x.semester(x)')", "DEUTSCH Which semester?")
        self.addForm("Ask('?x.kurs(x)')", "DEUTSCH Which course?")
