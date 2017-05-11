# Test data for PyObjectTest.java


class DelTrigger(object):
    def __del__(self):
        global del_triggered
        del_triggered = True


class EmptyObject(object):
    pass


class SimpleObject(object):
    def __init__(self):
        self.one = 1
        self.two = 2
        self.three = 3

    def __dir__(self):
        return self.__dict__.keys()


def sum_mul(*args, **kwargs):
    mul = kwargs.pop("mul", 1)
    div = kwargs.pop("div", 1)
    return sum(args) * mul / div


def is_none(x):
    return x is None


none_var = None
bool_var = True
int_var = 42
float_var = 43.5
str_var = "hello"
