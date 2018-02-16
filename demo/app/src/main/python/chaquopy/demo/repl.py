from __future__ import absolute_import, division, print_function

from code import InteractiveConsole
import sys


class AndroidConsole(InteractiveConsole):
    """`interact` must be run on a background thread, because it blocks waiting for input.
    """
    def __init__(self, context):
        InteractiveConsole.__init__(self, locals={"context": context.getApplicationContext()})

    def interact(self, banner=None):
        if banner is None:
            banner = ("Python {} on {}\n".format(sys.version, sys.platform) +
                      "The current application context is available in the variable 'context'.")
        try:
            InteractiveConsole.interact(self, banner)
        except SystemExit:
            pass
