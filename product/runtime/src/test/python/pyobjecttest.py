# Test data for PyObjectTest.java


class DelTrigger(object):
    def __del__(self):
        global del_triggered
        del_triggered = True


to_remove = abs     # Arbitrary built-in object
