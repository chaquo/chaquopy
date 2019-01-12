package com.chaquo.python;

import java.util.*;

import static com.chaquo.python.ContainerUtils.callAttr;

abstract class PyIterator<T> implements Iterator<T> {
    private PyObject iter;
    private boolean hasNextElem = true;
    private PyObject nextElem;

    public PyIterator(PyObject obj) {
        iter = callAttr(obj, "__iter__");
        updateNext();
    }

    protected void updateNext() {
        try {
            nextElem = iter.callAttr("__next__");
        } catch (PyException e) {
            if (e.getMessage().startsWith("StopIteration:")) {
                hasNextElem = false;
                nextElem = null;
            } else {
                throw e;
            }
        }
    }

    @Override public boolean hasNext() {
        return hasNextElem;
    }

    @Override public T next() {
        if (!hasNext()) throw new NoSuchElementException();
        T result = makeNext(nextElem);
        updateNext();
        return result;
    }

    protected abstract T makeNext(PyObject element);

    @Override public void remove() {
        throw new UnsupportedOperationException(
            "Python does not support removing from a container while iterating over it");
        // The removal would succeed, but the iterator would refuse to continue.
    }
}
