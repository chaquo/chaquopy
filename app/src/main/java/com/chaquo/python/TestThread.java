package com.chaquo.python;

public class TestThread {

    public static class BlockingConstructor {
        public BlockingConstructor(long delay) {
            BlockingMethods.blockStatic(delay);
        }
    }

    public static class BlockingMethods {

        public void blockInstance(long delay) {
            blockStatic(delay);
        }

        public static void blockStatic(long delay) {
            try {
                Thread.sleep(delay);
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
        }
    }

}
