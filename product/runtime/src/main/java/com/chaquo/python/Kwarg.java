package com.chaquo.python;

import org.jetbrains.annotations.*;

/** A Python keyword argument. These may be passed at the end of the parameter list of
 * {@link PyObject#call PyObject.call()}. */
public class Kwarg {
    public @NotNull String key;
    public Object value;

    /** The value will be converted as described at {@link PyObject#fromJava
     * PyObject.fromJava()}. */
    public Kwarg(@NotNull String key, Object value) {
        this.key = key;
        this.value = value;
    }
}
