#!/usr/bin/env python3
#
# Converts output of javap -s to a Python proxy class definition.
#
# ( for c in java.lang.Class java.lang.Object java.lang.reflect.Modifier
# java.lang.reflect.Method java.lang.reflect.Field java.lang.reflect.Constructor; do javap
# -public -s $c | ./make_proxy.py; echo; done ) > bootstrap.py

from collections import defaultdict
import re
import sys


METHOD_MODIFIERS = ["abstract", "final", "native", "private", "protected", "public", "static",
                    "strictfp", "synchronized"]
DESCRIPTOR_RE = r"descriptor: (.+)$"
OBJECT_METHODS = {
    "equals":       [('(Ljava/lang/Object;)Z', False, False)],
    "getClass":     [('()Ljava/lang/Class;', False, False)],
    "hashCode":     [('()I', False, False)],
    "notify":       [('()V', False, False)],
    "notifyAll":    [('()V', False, False)],
    "toString":     [('()Ljava/lang/String;', False, False)],
    "wait":         [('(J)V', False, False), ('(JI)V', False, False), ('()V', False, False)],
}


def main():
    methods = defaultdict(list)
    class_name = None
    method_name = None
    field_name = None

    in_file = sys.stdin
    for line_no, line in enumerate(in_file, start=1):
        try:
            line = line.strip()
            if not line or line == "}":
                continue

            if class_name is None:
                if line.startswith("Compiled from"):
                    pass
                else:
                    match = re.match(r"(.+ )?class (\S+?)(<.+>)? ", line)
                    if not match:
                        raise ValueError("Invalid top-level line")
                    class_name = match.group(2)

            elif method_name:
                match = re.match(DESCRIPTOR_RE, line)
                assert match
                methods[method_name].append((match.group(1), static, varargs))
                method_name = None

            elif field_name:
                assert re.match(DESCRIPTOR_RE, line)
                field_name = None   # Fields not implemented

            else:
                assert line.endswith(";")
                method_name = field_name = None
                if "(" in line:
                    static = False
                    varargs = "..." in line
                    for word in line.split():
                        if word in METHOD_MODIFIERS:
                            if word == "static":
                                static = True
                        elif "(" in word:
                            method_name = word.split("(")[0]
                            break
                    assert method_name
                else:
                    field_name = "fields not implemented"

        except Exception as e:
            raise ValueError("{}:{}: {}".format(in_file.name, line_no, line)) from e

    methods.update((k,v) for k,v in OBJECT_METHODS.items() if k not in methods)

    print("class {}(with_metaclass(JavaClass, JavaObject)):".format(class_name.split(".")[-1]))
    print("    _chaquopy_clsname = {!r}".format(class_name))
    for method_name in sorted(methods.keys()):
        overloads = methods[method_name]
        if len(overloads) == 1:
            print("    {} = {}".format(method_name, format_method(overloads[0])))
        else:
            print("    {} = JavaMultipleMethod([".format(method_name))
            print("        " + ",\n        ".join(map(format_method, overloads)) + "])")


def format_method(overload):
    signature, static, varargs = overload
    return "JavaMethod({!r}{}{})".format(signature,
                                         ", static=True" if static else "",
                                         ", varargs=True" if varargs else "")


if __name__ == "__main__":
    main()
