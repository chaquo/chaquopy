from __future__ import absolute_import, division, print_function

from code import InteractiveConsole
import sys
from threading import Event

from java import dynamic_proxy
from java.lang import Runnable

if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue


class AndroidConsole(InteractiveConsole):
    """`interact` must be run on a background thread, because it blocks waiting for input. However, 
    all entered code is executed on the UI thread, so it can safely call UI APIs.
    """
    def __init__(self, repl_activity):
        self.repl_activity = repl_activity
        InteractiveConsole.__init__(self, locals=dict(context=repl_activity))

    def interact(self, banner=None):
        if banner is None:
            banner = ("Python {} on {}\n".format(sys.version, sys.platform) +
                      "The current activity context is available in the variable 'context'.")
        try:
            InteractiveConsole.interact(self, banner)
        except SystemExit:
            pass

    def runcode(self, code):
        exc_q = Queue()
        class R(dynamic_proxy(Runnable)):
            def run(r_self):
                try:
                    InteractiveConsole.runcode(self, code)
                except BaseException as e:
                    exc_q.put(e)
                else:
                    exc_q.put(None)

        self.repl_activity.runOnUiThread(R())
        exc = exc_q.get()
        if exc is not None:
            raise exc
