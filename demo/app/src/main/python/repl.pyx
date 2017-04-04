from code import InteractiveInterpreter
import sys
from StringIO import StringIO


sys.stdout = sys.stderr = StringIO()
interp = InteractiveInterpreter()

# TODO:  multi-line input (InteractiveConsole)
cdef public repl_exec(line):
    interp.runsource(line)

    sio = sys.stdout
    result = sio.getvalue()
    sio.seek(0)
    sio.truncate(0)
    return result
