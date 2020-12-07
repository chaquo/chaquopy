"""Test data for PyObjectTest.java"""

from time import sleep, time

from java.lang import System


# See also equivalent Java implementation in TestReflect.java.
#
# As well as the Java PyObjectTest, this class is also used in the Python tests test_proxy and
# test_static_proxy
class DelTrigger(object):
    TIMEOUT = 1.0
    triggered = False

    def __del__(self):
        DelTrigger.triggered = True

    @staticmethod
    def reset():
        DelTrigger.triggered = False

    @staticmethod
    def assertTriggered(test, expected):
        deadline = time() + DelTrigger.TIMEOUT
        while time() < deadline:
            System.gc()
            System.runFinalization()
            try:
                test.assertEqual(expected, DelTrigger.triggered)
                return
            except AssertionError:
                if not expected:
                    raise
            sleep(DelTrigger.TIMEOUT / 10)
        test.fail("Not triggered after {} seconds".format(DelTrigger.TIMEOUT))


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
    return sum(args) * mul // div


def throws_java(msg="abc olé 中文"):
    from java.io import IOException
    raise IOException(msg)

def throws_python(msg="abc olé 中文"):
    raise ValueError(msg)


def get_none():
    return

def is_none(x):
    return x is None


none_var = None
bool_var = True
int_var = 42
negative_int_var = -42
short_int_var = 1234
medium_int_var = 123456
long_int_var = 9876543210
super_long_int_var = 9876543210876543210
float_var = 43.5
double_var = 1e39
str_var = "hello"
char_var = "x"

class ManyAttributes:
    def __init__(self):
        for i in range(1000):
            setattr(self, str(i), str(i))
many_attributes = ManyAttributes()

char_list_var = ["a", "b", "c"]
int_list_var = [11, 22, 33]
bytes_var = b"\x00\x01\x7f\x80\xfe\xff"
generator_var = (x for x in range(42))


class HashObject(object):
    def __init__(self, x):
        self.x = x

    def __hash__(self):
        return self.x
