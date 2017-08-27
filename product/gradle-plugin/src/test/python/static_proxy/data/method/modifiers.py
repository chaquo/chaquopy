from java import *

from com.example import Class1, Class2


class C(static_proxy(None)):
    @method(jvoid, [])
    def default(*args):
        pass

    @method(jvoid, [], modifiers="")
    def nothing(*args):
        pass

    @method(jvoid, [], modifiers="protected")
    def protected_(*args):
        pass

    @method(jvoid, [], modifiers="public final")
    def public_final(*args):
        pass

    @method(jvoid, [], modifiers="@Override public")
    def override_manual(*args):
        pass

    @Override(jvoid, [])
    def override_decorator(*args):
        pass

    @Override(jvoid, [], modifiers="protected")
    def override_both(*args):
        pass
