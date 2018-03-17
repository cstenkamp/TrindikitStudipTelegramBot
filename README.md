# Trindikit - Studip - Telegram- Bot
Project for the class "Dialogue systems and embodied conversational agents" in WS2017/2018: a telegram-bot that uses a python-version of "Trindikit", an information state approach dialogue manager, to access StudIP of the Uni Osnabrück with a Telegram Chatbot

This projects builds on the Python-implementation of the ISU approach, available under the GNU GENERAL PUBLIC LICENSE.

* (relatively short) Report of the project: http://www.cstenkamp.de/StudipTelegramBot_report.pdf
* Information State Approach intro: http://www.cstenkamp.de/ISA_presentation.pdf
* Paper for the original Trindikit-Python implementation: http://www.cse.chalmers.se/~peb/pubs/Ljunglof2009a%20-%20trindikit.py%20An%20open-source%20Python%20library.pdf

## Sample Conversation:

U> /start
S: To use Stud.IP capabilities, start by sending the message 'studip' to the bot. After that, you must enter your Stud.IP username and password, such that you can use most of the functionalities of this bot<br/>
S: Hello.<br/>
U> studip<br/>
S: Before we start, I need to know your username. What is it?<br/>
U> cstenkamp<br/>
S: Next up, your password please.<br/>
U> PASSWORD<br/>
S: Unfortunately, to have access to your StudIP-Files, I have to save the username and pw. The only thing I can do is to obfuscate the Username and PW to a Hex-string.<br/>
S: The Auth-string is: OBFUSCATED_STRING<br/>
U> download from Datenbanksysteme<br/>
S: Which file from that course do you want to download?<br/>
U> dbs 2017<br/>
S: You underspecified which course you mean! Do you mean Datenbanksysteme in SS 2018 or SS 2017?<br/>
S: Which semester?<br/>
U> SS 17<br/>
S: There is no file with that name! Do you mean 'dbs2017_01.pdf' or 'dbs2017_02.pdf' or 'dbs2017_03.pdf'?<br/>
S: Which file from that course do you want to download?<br/>
U> dbs2017_01.pdf<br/>
S: The file you requested is on its way!<br/>
S: <send File>
  


## Sample Sentences the system can handle:
* Ist gerade Vorlesungszeit?
* In wie vielen Tagen geht das Semester los?
* Wann geht das Semester los?
* In wie vielen Tagen gehen die Semesterferien los?
* Wann gehen die Semesterferien los?
* Wann ist ein Semester? -> `<semester`> / Wann ist nächstes Semester? / Wann ist `<semester`>?
* Was für Kurse habe ich in `<semester`>?
* What is my next Session? / What is my next Session of `<Kurs`>? / What is my next Session of `<semester`>? / What is my next session of -> `<semester`>
* When is my next Session? / When is my next Session of `<Kurs`>? / When is my next Session of `<semester`>? / When is my next session of -> `<semester`>
* Where is my next Session? / Where is my next Session of `<Kurs`>? / Where is my next Session of `<semester`>? / Where is my next session of -> `<semester`>
* When is the exam of `<Kurs`>?
* What courses do I have left today?
* What courses do I have on `<day`>?
* List all files in `<Course`>
* Download a file from `<Kurs`> -> [nach Bedarf `<semester`> ->] `<filename`> [nach Bedarf -> `<correctedName`>]
