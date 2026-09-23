package com.chaquo.python;

import static org.junit.Assert.*;

import androidx.test.ext.junit.runners.*;

import com.chaquo.python.utils.*;

import org.junit.*;
import org.junit.runner.*;


// The Java tests aren't currently included, because:
//   * It would require extensive refactoring of the JavaTestActivity and the way it
//     interacts with the console.
//   * The Java tests never vary by architecture anyway, only by API level, so manual
//     testing on a single architecture is good enough.
@RunWith(AndroidJUnit4.class)
public class ChaquopyTests {
    @Test public void testPython() {
        PyObject result = PythonTestActivity.runTests();
        assertTrue(result.callAttr("wasSuccessful").toBoolean());
    }
}
