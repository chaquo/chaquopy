package com.chaquo.python.demo;

import android.view.textclassifier.*;

@SuppressWarnings("unused")
public class TestAndroidReflect {
    public TextClassifier tcFieldPublic;
    protected TextClassifier tcFieldProtected;

    public TextClassifier tcMethodPublic() { return null; }
    protected TextClassifier tcMethodProtected() { return null; }

    public int iFieldPublic;
    protected int iFieldProtected;

    public int iMethodPublic() { return 0; }
    protected int iMethodProtected() { return 0; }

    @Override
    protected void finalize() {}
}
