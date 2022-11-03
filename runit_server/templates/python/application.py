#from packages import request

def index():
    print('Yay, Python works')

def counter():
    print([i for i in range(0, 9)])

def printout(string):
    print(string)

def time():
    from datetime import datetime
    print((datetime.utcnow()).strftime("%a %b %d %Y %H:%M:%S"))

def quote():
    from collections import namedtuple
    from random import choice
 
    Quote = namedtuple("Quote", ("text", "author"))
 
    quotes = [
        Quote("Talk is cheap. Show me the code.", "Linus Torvalds"),
        Quote("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
        Quote("Always code as if the guy who ends up maintaining your code will be a violent psychopath who knows where you live",
              "John Woods"),
        Quote("Give a man a program, frustrate him for a day. Teach a man to program, frustrate him for a lifetime.", "Muhammad Waseem"),
        Quote("Progress is possible only if we train ourselves to think about programs without thinking of them as pieces of executable code. ",
              "Edsger W. Dijkstra")
    ]
    print(choice(quotes)._asdict())
