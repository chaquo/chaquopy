package com.chaquo.python.utils;

import android.os.*;
import android.support.annotation.*;
import java.util.*;

/** Similar to SimpleLiveEvent, but any values set while inactive will be buffered. As soon as
 * we have an active observer, it will be notified of those values in the same order as they were
 * set. */
public class BufferedLiveEvent<T> extends SingleLiveEvent<T> {

    private ArrayList<T> mBuffer = new ArrayList<>();
    private Handler mHandler = new Handler(Looper.getMainLooper());

    /** Unlike in the base class, multiple calls to postData will always result in multiple values
     * being notified to the observer. */
    @Override public void postValue(@Nullable final T value) {
        mHandler.post(new Runnable() {
            @Override public void run() {
                setValue(value);
            }
        });
    }

    @Override public void setValue(@Nullable T t) {
        if (hasActiveObservers()) {
            super.setValue(t);
        } else {
            mBuffer.add(t);
        }
    }

    @Override protected void onActive() {
        for (T t : mBuffer) {
            super.setValue(t);
        }
        mBuffer.clear();
    }

}
