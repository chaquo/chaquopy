package com.chaquo.python.demo;

import com.chaquo.python.*;

public class PythonTestActivity extends UnitTestActivity {

    @Override
    protected void runTests() {
        Python python = Python.getInstance();
        PyObject unittest = python.getModule("unittest");
        PyObject suite = python.getModule("test_suite");
        PyObject stream = python.getModule("sys").get("stdout");
        PyObject runner = unittest.callAttr("TextTestRunner",
                                            new Kwarg("stream", stream),
                                            new Kwarg("verbosity", 2));
        PyObject loader = unittest.get("defaultTestLoader");
        runner.callAttr("run", loader.callAttr("loadTestsFromModule", suite));
    }

}
