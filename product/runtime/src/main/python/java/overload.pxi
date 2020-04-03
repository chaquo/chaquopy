cdef is_applicable(CQPEnv env, sign_args, args, autobox, varargs):
    if len(args) == len(sign_args):
        pass
    elif varargs:
        if len(args) < len(sign_args) - 1:
            return False
    else:
        return False

    for index, sign_arg in enumerate(sign_args):
        if varargs and (index == len(sign_args) - 1):
            assert sign_arg[0] == "["
            remaining_args = args[index:]
            return is_applicable(env, [sign_arg[1:]] * len(remaining_args),
                                 remaining_args, autobox, False)
        else:
            arg = args[index]
        if not is_applicable_arg(env, sign_arg, arg, autobox):
            return False

    return True


# Because of the caching in JavaMultipleMethod, the result of this function must only be
# affected by the actual parameter type, not its value.
cdef is_applicable_arg(CQPEnv env, r, arg, autobox):
    # All Python iterable types are considered applicable to all array types. (p2j would
    # type-check the values, possibly leading to incorrect overload caching.)
    if assignable_to_array(env, r, arg):
        return True
    try:
        p2j(env.j_env, r, arg, autobox)
        return True
    except TypeError:
        return False


cdef better_overload(CQPEnv env, JavaMethod jm1, JavaMethod jm2, actual_types, varargs):
    """Returns whether jm1 is an equal or better match than jm2 for the given actual parameter
    types. This is based on JLS 15.12.2.5. "Choosing the Most Specific Method" and JLS 4.10.
    "Subtyping".
    """
    defs1, defs2 = jm1.args_sig, jm2.args_sig

    if varargs:
        if not actual_types:
            # No arguments were given, so the definitions must both be of the form (X...). Give
            # a fake argument so they can be compared.
            actual_types = [type(None)]
        defs1 = extend_varargs(defs1, len(actual_types))
        defs2 = extend_varargs(defs2, len(actual_types))

    return (len(defs1) == len(defs2) and
            all([better_overload_arg(env, d1, d2, at)
                 for d1, d2, at in zip(defs1, defs2, actual_types)]))


cdef extend_varargs(defs, length):
    varargs_count = length - (len(defs) - 1)
    vararg_type = defs[-1][1:]
    return defs[:-1] + ((vararg_type,) * varargs_count)


# Because of the caching in JavaMultipleMethod, the result of this function must only be
# affected by the actual parameter types, not their values.
#
# We don't have to handle combinations which will be filtered out by is_applicable_arg. For
# example, we'll never be asked to compare a numeric type with a boolean or char, because any
# actual parameter type which is applicable to one will not be applicable to the others.
#
# In this context, boxed and unboxed types are NOT treated as related.
cdef better_overload_arg(CQPEnv env, def1, def2, actual_type):
    if def2 == def1:
        return True

    # To avoid data loss, we prefer to treat a Python int or float as the largest of the
    # corresponding Java types.
    elif issubclass(actual_type, int) and (def1 in INT_TYPES) and (def2 in INT_TYPES):
        return dict_index(INT_TYPES, def1) <= dict_index(INT_TYPES, def2)
    elif issubclass(actual_type, float) and (def1 in FLOAT_TYPES) and (def2 in FLOAT_TYPES):
        return dict_index(FLOAT_TYPES, def1) <= dict_index(FLOAT_TYPES, def2)

    # Similarly, we prefer to treat a Python string as a Java String rather than a character.
    # (Its length cannot be taken into account: see note above about caching.)
    elif issubclass(actual_type, unicode) and \
         def2 in ["C", "Ljava/lang/Character;"] and \
         env.IsAssignableFrom(env.FindClass("Ljava/lang/String;"), env.FindClass(def1)):
        return True

    # Otherwise we prefer the smallest (i.e. most specific) Java type. This includes the case
    # of passing a Python int where float and double overloads exist: the float overload will
    # be called, just like in Java.
    elif (def1 in NUMERIC_TYPES) and (def2 in NUMERIC_TYPES):
        return dict_index(NUMERIC_TYPES, def1) >= dict_index(NUMERIC_TYPES, def2)

    elif def2.startswith("L"):
        if def1.startswith("L"):
            return env.IsAssignableFrom(env.FindClass(def1), env.FindClass(def2))
        elif def1.startswith("["):
            return def2 in ARRAY_CONVERSIONS
    elif def2.startswith("["):
            return (def2[1] not in PRIMITIVE_TYPES and
                    def1.startswith("[") and
                    better_overload_arg(env, def1[1:], def2[1:], type(None)))

    return False
