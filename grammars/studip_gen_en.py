import ibis_generals


class StudIP_gen_grammar(ibis_generals.SimpleGenGrammar):
    def addForms(self):
        self.addForm("Answer(YesNo(False))", "No.")
        self.addForm("Answer(YesNo(True))", "Yes.")

        self.addForm("Ask('?x.username(x)')", "Before we start, I need to know your username. What is it?")
        self.addForm("Ask('?x.password(x)')", "Next up, your password please.")
        self.addForm("State('wtf')", "Uhm, wtf")
        self.addForm("Ask('?x.coursename(x)')", "From which course do you want to download?")
        self.addForm("Ask('?x.filename(x)')", "Which file from that course do you want to download?")
        self.addForm("Ask('?x.semester(x)')", "Which semester?")
        self.addForm("Ask('?x.kurs(x)')", "Which course?")
