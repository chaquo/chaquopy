package com.chaquo.python;

/** A Python keyword argument. These may be passed at the end of the parameter list of
 * {@link PyObject#call PyObject.call()}. */
public class Kwarg {
    public String key;
    public Object value;

    public Kwarg(String key, Object value) {
        this.key = key;
        this.value = value;
    }
}
