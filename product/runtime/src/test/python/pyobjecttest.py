# Test data for PyObjectTest.java


class DelTrigger(object):
    def __del__(self):
        global del_triggered
        del_triggered = True


to_remove = abs     # Arbitrary built-in object


class SimpleObject(object):
    def __init__(self):
        self.one = 1
        self.two = 2
        self.three = 3

    def __dir__(self):
        return self.__dict__.keys()


def return_none():
    return None

def is_none(x):
    return x is None
