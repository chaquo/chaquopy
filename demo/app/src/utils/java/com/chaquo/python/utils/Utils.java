package com.chaquo.python.utils;

import android.content.*;
import android.content.res.*;

public class Utils {
    /** Make this package easy to copy to other apps by avoiding direct "R" references. (It
     * would be better to do this by distributing it along with its resources in an AAR, but
     * Chaquopy doesn't support getting Python code from an AAR yet.)*/
    public static int resId(Context context, String type, String name) {
        Resources resources = context.getResources();
        return resources.getIdentifier(name, type, context.getApplicationInfo().packageName);
    }
}
