package com.chaquo.python.demo;


// Some of the members of this class refer to classes which don't exist at runtime
// (see test_reflect.py). This is done by putting them in a compileOnly dependency in
// build.gradle.kts.
@SuppressWarnings("unused")
public class TestAndroidReflect {
    public CompileOnly coFieldPublic;
    protected CompileOnly coFieldProtected;

    public CompileOnly coMethodPublic() { return null; }
    protected CompileOnly coMethodProtected() { return null; }

    public int iFieldPublic;
    protected int iFieldProtected;

    public int iMethodPublic() { return 0; }
    protected int iMethodProtected() { return 0; }

    @Override
    protected void finalize() {}
}
