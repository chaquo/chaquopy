package com.chaquo.python.demo;

import android.app.*;
import com.chaquo.python.utils.*;
import java.io.*;
import org.junit.runner.*;
import org.junit.runner.notification.*;

public class JavaTestActivity extends ConsoleActivity {

    @Override protected Class<? extends JavaTestTask> getTaskClass() {
        return JavaTestTask.class;
    }

    // =============================================================================================

    public static class JavaTestTask extends Task {

        public JavaTestTask(Application app) {
            super(app);
        }

        @Override public void run() {
            JUnitCore juc = new JUnitCore();
            juc.addListener(new Listener());
            juc.run(com.chaquo.java.TestSuite.class);
        }

        private class Listener extends RunListener {
            private ByteArrayOutputStream stdout = new ByteArrayOutputStream();
            private ByteArrayOutputStream stderr = new ByteArrayOutputStream();

            @Override
            public void testRunStarted(Description description) throws Exception {
                System.setOut(new PrintStream(stdout));
                System.setErr(new PrintStream(stderr));
            }

            @Override
            public void testStarted(Description description) throws Exception {
                output(description.toString() + "\n");
            }

            @Override
            public void testIgnored(Description description) throws Exception {
                output("IGNORED\n");
            }

            @Override
            public void testFinished(Description description) throws Exception {
                output(stdout.toString());
                stdout.reset();
                outputError(stderr.toString());
                stderr.reset();
            }

            @Override
            public void testFailure(Failure failure) throws Exception {
                String trace = failure.getTrace();
                StringBuilder filteredTrace = new StringBuilder();
                boolean filterOn = false;
                int lineNum = 0;
                for (String line : trace.split("\n")) {
                    lineNum++;
                    if (lineNum > 1 && line.matches(".*org.junit.*")) {
                        filterOn = true;
                    } else {
                        if (filterOn) {
                            filteredTrace.append("...\n");
                            filterOn = false;
                        }
                        filteredTrace.append(line).append("\n");
                    }
                }
                outputError(filteredTrace);
            }

            @Override
            public void testAssumptionFailure(Failure failure) {
                outputError("ASSUMPTION FAILED\n");
            }

            @Override
            public void testRunFinished(Result result) throws Exception {
                String message = String.format(
                    "Ran %s tests in %.3f seconds (%s failed, %s ignored)\n",
                    result.getRunCount(), result.getRunTime() / 1000.0,
                    result.getFailureCount(), result.getIgnoreCount());
                if (result.getFailureCount() > 0) {
                    outputError(message);
                } else {
                    output(message);
                }
            }
        }
    }

}
