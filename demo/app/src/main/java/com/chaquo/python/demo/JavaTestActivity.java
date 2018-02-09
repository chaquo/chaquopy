package com.chaquo.python.demo;

import com.chaquo.java.*;
import org.junit.runner.*;
import org.junit.runner.notification.*;

public class JavaTestActivity extends UnitTestActivity {

    @Override
    protected void runTests() {
        for (int i = 0; i < 50; i++) {
            output("FILLER " + i + "\n");
        }

        try {
            Thread.sleep(5000);
        } catch (InterruptedException e) {}


        for (int i = 0; i < 20; i++) {
            output(i + "\n");
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {}
        }
        /* FIXME
        JUnitCore juc = new JUnitCore();
        juc.addListener(new Listener());
        juc.run(TestSuite.class);
        */
    }

    private class Listener extends RunListener {
        @Override
        public void testStarted(Description description) throws Exception {
            output(description.toString() + "\n");
        }

        @Override
        public void testIgnored(Description description) throws Exception {
            output("IGNORED\n");
        }

        @Override
        public void testFailure(Failure failure) throws Exception {
            String trace = failure.getTrace();
            StringBuilder filteredTrace = new StringBuilder();
            boolean filterOn = false;
            for (String line : trace.split("\n")) {
                if (line.matches(".*org.junit.*")) {
                    filterOn = true;
                } else {
                    if (filterOn) {
                        filteredTrace.append("...\n");
                        filterOn = false;
                    }
                    filteredTrace.append(line).append("\n");
                }
            }
            output(filteredTrace.toString());
        }

        @Override
        public void testAssumptionFailure(Failure failure) {
            output("ASSUMPTION FAILED\n");
        }

        @Override
        public void testRunFinished(Result result) throws Exception {
            output(String.format("Ran %s tests in %.3f seconds (%s failed, %s ignored)\n",
                                 result.getRunCount(), result.getRunTime() / 1000.0,
                                 result.getFailureCount(), result.getIgnoreCount()));
        }
    }

}
