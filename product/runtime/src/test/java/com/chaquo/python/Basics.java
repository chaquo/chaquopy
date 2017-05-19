package com.chaquo.python;

import java.lang.String;

/** See test_basics.py */
public class Basics {
	static public boolean methodStaticZ() { return fieldStaticZ; }
	static public byte methodStaticB() { return fieldStaticB; }
	static public char methodStaticC() { return fieldStaticC; }
	static public short methodStaticS() { return fieldStaticS; }
	static public int methodStaticI() { return fieldStaticI; }
	static public long methodStaticJ() { return fieldStaticJ; }
	static public float methodStaticF() { return fieldStaticF; }
	static public double methodStaticD() { return fieldStaticD; }
	static public String methodStaticString() { return fieldStaticString; }
	static public String methodStaticParamsString(String s) { return s; }

    public boolean methodZ() { return fieldZ; }
    public byte methodB() { return fieldB; }
    public char methodC() { return fieldC; }
    public short methodS() { return fieldS; }
    public int methodI() { return fieldI; }
    public long methodJ() { return fieldJ; }
    public float methodF() { return fieldF; }
    public double methodD() { return fieldD; }
    public String methodString() { return fieldString; }
	public void methodException(int depth) throws IllegalArgumentException {
		if (depth == 0) throw new IllegalArgumentException("helloworld");
		else methodException(depth -1);
	}
	public void methodExceptionChained() throws IllegalArgumentException {
		try {
			methodException(5);
		} catch (IllegalArgumentException e) {
			throw new IllegalArgumentException("helloworld2", e);
		}
	}

	static public boolean fieldStaticZ = true;
	static public byte fieldStaticB = 127;
	static public char fieldStaticC = 'k';
	static public short fieldStaticS = 32767;
	static public int fieldStaticI = 2147483467;
	static public long fieldStaticJ = 9223372036854775807L;
	static public float fieldStaticF = 1.23456789f;
	static public double fieldStaticD = 1.23456789;
	static public String fieldStaticString = "staticworld";
    static public final String fieldStaticFinalString = "staticfinalworld";

	public boolean fieldZ = true;
	public byte fieldB = 127;
	public char fieldC = 'k';
	public short fieldS = 32767;
	public int fieldI = 2147483467;
	public long fieldJ = 9223372036854775807L;
	public float fieldF = 1.23456789f;
	public double fieldD = 9.87654321;
    public Object fieldObject = null;
    public CharSequence fieldCharSequence = null;
    public String fieldString = "helloworld";
    public Class fieldClass = null;
    public final String fieldFinalString = "finalworld";

	// Floating-point comparison epsilon
	private final static double EPSILON = 1E-6;

    public Basics() {}
    public Basics(byte fieldBVal) {
        fieldB = fieldBVal;
    }

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

	public boolean methodParamsZBCSIJFD(boolean x1, byte x2, char x3, short x4,
			int x5, long x6, float x7, double x8) {
		return (x1 == true && x2 == 127 && x3 == 'k' && x4 == 32767 &&
				x5 == 2147483467 && x6 == 9223372036854775807L &&
				(Math.abs(x7 - 1.23456789f) < EPSILON) &&
				(Math.abs(x8 - 1.23456789) < EPSILON));
	}

	public boolean methodParamsString(String s) {
		return (s.equals("helloworld"));
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

}
