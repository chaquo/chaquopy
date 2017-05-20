package com.chaquo.python;

public class TestArrays {
	public boolean[] methodArrayZ() {
		boolean[] x = new boolean[3];
		x[0] = x[1] = x[2] = true;
		return x;
	}
	public byte[] methodArrayB() {
		byte[] x = new byte[3];
		x[0] = x[1] = x[2] = 127;
		return x;
	}
	public char[] methodArrayC() {
		char[] x = new char[3];
		x[0] = x[1] = x[2] = 'k';
		return x;
	}
	public short[] methodArrayS() {
		short[] x = new short[3];
		x[0] = x[1] = x[2] = 32767;
		return x;
	}
	public int[] methodArrayI() {
		int[] x = new int[3];
		x[0] = x[1] = x[2] = 2147483467;
		return x;
	}
	public long[] methodArrayJ() {
		long[] x = new long[3];
		x[0] = x[1] = x[2] = 9223372036854775807L;
		return x;
	}
	public float[] methodArrayF() {
		float[] x = new float[3];
		x[0] = x[1] = x[2] = 1.23456789f;
		return x;
	}
	public double[] methodArrayD() {
		double[] x = new double[3];
		x[0] = x[1] = x[2] = 1.23456789;
		return x;
	}
	public String[] methodArrayString() {
		String[] x = new String[3];
		x[0] = x[1] = x[2] = "helloworld";
		return x;
	}

    private final static double EPSILON = 1E-6;

	public boolean methodParamsZBCSIJFD(boolean x1, byte x2, char x3, short x4,
										int x5, long x6, float x7, double x8) {
		return (x1 == true && x2 == 127 && x3 == 'k' && x4 == 32767 &&
			x5 == 2147483467 && x6 == 9223372036854775807L &&
			(Math.abs(x7 - 1.23456789f) < EPSILON) &&
			(Math.abs(x8 - 1.23456789) < EPSILON));
	}

	public boolean methodParamsArrayI(int[] x) {
		if (x.length != 3)
			return false;
		return (x[0] == 1 && x[1] == 2 && x[2] == 3);
	}

	public boolean methodParamsArrayString(String[] x) {
		if (x.length != 2)
			return false;
		return (x[0].equals("hello") && x[1].equals("world"));
	}

	public boolean methodParamsObject(Object x) {
		return true;
	}

	public Object methodReturnStrings() {
		String[] hello_world = new String[2];
		hello_world[0] = "Hello";
		hello_world[1] = "world";
		return hello_world;
	}

	public Object methodReturnIntegers() {
		int[] integers = new int[2];
		integers[0] = 1;
		integers[1] = 2;
		return integers;
	}

	public boolean methodParamsArrayByte(byte[] x) {
		if (x.length != 3)
			return false;
		return (x[0] == 127 && x[1] == 127 && x[2] == 127);
	}

	public void fillByteArray(byte[] x) {
		if (x.length != 3)
			return;
		x[0] = 127;
		x[1] = 1;
		x[2] = -127;
	}

	public static boolean methodParamsMatrixI(int[][] x) {
		if (x.length != 3 || x[0].length != 3)
			return false;
		return (x[0][0] == 1 && x[0][1] == 2 && x[1][2] == 6);
	}
	public static int[][] methodReturnMatrixI() {
        int[][] matrix = {{1,2,3},
                          {4,5,6},
                          {7,8,9}};
        return matrix;
	}

}
