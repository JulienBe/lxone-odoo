import sys
from picklingtools.xmldumper import *

xd = XMLDumper(sys.stdout)
data = {'a': {'b': 'c', 'd': 'e'}, 'f': {'g': ['h','i','j'], 'k': {'l': None}, 'a': {'b': 'c'}}}
xd.XMLDumpKeyValue('first', data)


