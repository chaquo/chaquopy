cdef jmethodID mid_getName = NULL

# To avoid infinite recursion, this function must not use anything which could call klass_sig
# itself. This includes any jclass proxy methods, and even CQPEnv methods, because they all call
# check_exception, which calls j2p.
cdef klass_sig(CQPEnv env, JNIRef j_cls):
    global mid_getName
    if not mid_getName:
        j_Class = env.FindClass("java.lang.Class")
        mid_getName = env.GetMethodID(j_Class, 'getName', '()Ljava/lang/String;')

    j_name = env.adopt(env.j_env[0].CallObjectMethod(env.j_env, j_cls.obj, mid_getName))
    if not j_name:
        env.ExceptionClear()
        raise Exception("Class.getName failed")
    return name_to_sig(j2p_string(env.j_env, j_name))


cdef object_sig(CQPEnv env, JNIRef j_obj):
    return klass_sig(env, env.GetObjectClass(j_obj))


# cpdef because it has unit tests.
cpdef jni_sig(c):
    if isinstance(c, unicode):
        sig_to_java(c)  # Check syntax
        return c.replace(".", "/")
    elif isinstance(c, type):
        if isinstance(c, JavaClass):
            if issubclass(c, JavaArray):
                return c.__name__
            else:
                return klass_sig(CQPEnv(), c._chaquopy_j_klass)
        elif issubclass(c, (NoneCast, java.Primitive)):
            return c.sig
    elif isinstance(c, jclass("java.lang.Class")):
        return name_to_sig(c.getName())
    else:
        raise TypeError("{} object does not specify a Java type".format(type(c).__name__))


# `name` must be in the format returned by Class.getName().
cdef name_to_sig(name):
    try:
        return java.primitives_by_name[name].sig
    except KeyError: pass

    if name.startswith("["):
        return name.replace(".", "/")
    else:
        return "L" + name.replace(".", "/") + ";"


cdef split_method_sig(definition):
    assert definition.startswith("(")
    argdef, ret = definition[1:].split(')')
    args = []

    while len(argdef):
        prefix = ''
        c = argdef[0]
        while c == '[':
            prefix += c
            argdef = argdef[1:]
            c = argdef[0]
        if c in 'ZBCSIJFD':
            args.append(prefix + c)
            argdef = argdef[1:]
            continue
        if c == 'L':
            c, argdef = argdef.split(';', 1)
            args.append(prefix + c + ';')
            continue
        raise ValueError("Invalid type code '{}' in definition '{}'".format(c, definition))

    return ret, tuple(args)


cdef sig_to_java(sig):
    try:
        return java.primitives_by_sig[sig].name
    except KeyError: pass

    if sig.startswith("["):
        return sig_to_java(sig[1:]) + "[]"
    if sig.startswith("L") and sig.endswith(";"):
        return sig[1:-1].replace("/", ".")
    raise ValueError("Invalid definition: '{}'".format(sig))


# `split_args_sig` is in the format of the args tuple returned by split_method_sig.
cdef args_sig_to_java(split_args_sig, varargs=False):
    formatted_args = []
    for i, sig in enumerate(split_args_sig):
        if varargs and i == (len(split_args_sig) - 1):
            assert sig.startswith("[")
            formatted_args.append(sig_to_java(sig[1:]) + "...")
        else:
            formatted_args.append(sig_to_java(sig))
    return "(" + ", ".join(formatted_args) + ")"
