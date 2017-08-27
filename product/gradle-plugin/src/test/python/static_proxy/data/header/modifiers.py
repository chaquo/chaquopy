from java import *


class Default(static_proxy(None)):
    pass

class Empty(static_proxy(None, modifiers="")):
    pass

class Protected(static_proxy(None, modifiers="protected")):
    pass

class PublicFinal(static_proxy(None, modifiers="public final")):
    pass
