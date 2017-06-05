from six import StringIO


class ForwardingOutputStream(StringIO):
    def __init__(self, obj, method):
        StringIO.__init__(self)
        self.func = getattr(obj, method)

    def write(self, s):
        StringIO.write(self, s)
        self.func(self.getvalue())
        self.seek(0)
        self.truncate(0)
