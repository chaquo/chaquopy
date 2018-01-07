package com.chaquo.python;

import java.lang.String;

/** See test_basics.py */
public class TestBasics {

    private final static double EPSILON = 1E-6;

    public boolean methodParamsZBCSIJFD(boolean x1, byte x2, char x3, short x4,
                                        int x5, long x6, float x7, double x8) {
        return (x1 == true && x2 == 127 && x3 == 'k' && x4 == 32767 &&
            x5 == 2147483467 && x6 == 9223372036854775807L &&
            (Math.abs(x7 - 1.23f) < EPSILON) &&
            (Math.abs(x8 - 9.87) < EPSILON));
    }

    // === Instance ==========================================================
    //
    // Fields are all initialized to a value different from any value used in the tests.

    public final boolean fieldFinalZ = false;
    public boolean fieldZ = false;
    public byte fieldB = 42;
    public char fieldC = 42;
    public short fieldS = 42;
    public int fieldI = 42;
    public long fieldJ = 42;
    public float fieldF = 42;
    public double fieldD = 42;

    public Object fieldObject = "42";

    public Number fieldNumber = 42;
    public Byte fieldByte = 42;
    public Short fieldShort = 42;
    public Integer fieldInteger = 42;
    public Long fieldLong = 42L;
    public Float fieldFloat = 42f;
    public Double fieldDouble = 42d;
    public Boolean fieldBoolean = false;
    public Character fieldCharacter = 42;

    public CharSequence fieldCharSequence = "42";
    public String fieldString = "42";

    public Class fieldKlass = TestBasics.class;

    public boolean[] fieldZArray = {false, false};
    public byte[] fieldBArray = {42};
    public char[] fieldCArray = {42};
    public short[] fieldSArray = {42};
    public int[] fieldIArray = {42};
    public long[] fieldJArray = {42};
    public float[] fieldFArray = {42};
    public double[] fieldDArray = {42};

    public Object[] fieldObjectArray = {"42"};

    public Number[] fieldNumberArray = {42};
    public Byte[] fieldByteArray = {42};
    public Short[] fieldShortArray = {42};
    public Integer[] fieldIntegerArray = {42};
    public Long[] fieldLongArray = {42L};
    public Float[] fieldFloatArray = {42f};
    public Double[] fieldDoubleArray = {42d};
    public Boolean[] fieldBooleanArray = {false, false};
    public Character[] fieldCharacterArray = {42};

    public CharSequence[] fieldCharSequenceArray = {"42"};
    public String[] fieldStringArray = {"42"};

    public Class[] fieldKlassArray = {TestBasics.class};


    public void noArgs() {}
    public void varargs1(Object arg0, Object... args) {}

    public boolean getZ() {
        return fieldZ;
    }

    public void setZ(boolean fieldZ) {
        this.fieldZ = fieldZ;
    }

    public byte getB() {
        return fieldB;
    }

    public void setB(byte fieldB) {
        this.fieldB = fieldB;
    }

    public char getC() {
        return fieldC;
    }

    public void setC(char fieldC) {
        this.fieldC = fieldC;
    }

    public short getS() {
        return fieldS;
    }

    public void setS(short fieldS) {
        this.fieldS = fieldS;
    }

    public int getI() {
        return fieldI;
    }

    public void setI(int fieldI) {
        this.fieldI = fieldI;
    }

    public long getJ() {
        return fieldJ;
    }

    public void setJ(long fieldJ) {
        this.fieldJ = fieldJ;
    }

    public float getF() {
        return fieldF;
    }

    public void setF(float fieldF) {
        this.fieldF = fieldF;
    }

    public double getD() {
        return fieldD;
    }

    public void setD(double fieldD) {
        this.fieldD = fieldD;
    }

    public Object getObject() {
        return fieldObject;
    }

    public void setObject(Object fieldObject) {
        this.fieldObject = fieldObject;
    }

    public Number getNumber() {
        return fieldNumber;
    }

    public void setNumber(Number fieldNumber) {
        this.fieldNumber = fieldNumber;
    }

    public Byte getByte() {
        return fieldByte;
    }

    public void setByte(Byte fieldByte) {
        this.fieldByte = fieldByte;
    }

    public Short getShort() {
        return fieldShort;
    }

    public void setShort(Short fieldShort) {
        this.fieldShort = fieldShort;
    }

    public Integer getInteger() {
        return fieldInteger;
    }

    public void setInteger(Integer fieldInteger) {
        this.fieldInteger = fieldInteger;
    }

    public Long getLong() {
        return fieldLong;
    }

    public void setLong(Long fieldLong) {
        this.fieldLong = fieldLong;
    }

    public Float getFloat() {
        return fieldFloat;
    }

    public void setFloat(Float fieldFloat) {
        this.fieldFloat = fieldFloat;
    }

    public Double getDouble() {
        return fieldDouble;
    }

    public void setDouble(Double fieldDouble) {
        this.fieldDouble = fieldDouble;
    }

    public Boolean getBoolean() {
        return fieldBoolean;
    }

    public void setBoolean(Boolean fieldBoolean) {
        this.fieldBoolean = fieldBoolean;
    }

    public Character getCharacter() {
        return fieldCharacter;
    }

    public void setCharacter(Character fieldCharacter) {
        this.fieldCharacter = fieldCharacter;
    }

    public CharSequence getCharSequence() {
        return fieldCharSequence;
    }

    public void setCharSequence(CharSequence fieldCharSequence) {
        this.fieldCharSequence = fieldCharSequence;
    }

    public String getString() {
        return fieldString;
    }

    public void setString(String fieldString) {
        this.fieldString = fieldString;
    }

    public Class getKlass() {
        return fieldKlass;
    }

    public void setKlass(Class fieldClass) {
        this.fieldKlass = fieldClass;
    }

    
    public boolean[] getZArray() {
        return fieldZArray;
    }

    public void setZArray(boolean[] fieldZArray) {
        this.fieldZArray = fieldZArray;
    }

    public byte[] getBArray() {
        return fieldBArray;
    }

    public void setBArray(byte[] fieldBArray) {
        this.fieldBArray = fieldBArray;
    }

    public char[] getCArray() {
        return fieldCArray;
    }

    public void setCArray(char[] fieldCArray) {
        this.fieldCArray = fieldCArray;
    }

    public short[] getSArray() {
        return fieldSArray;
    }

    public void setSArray(short[] fieldSArray) {
        this.fieldSArray = fieldSArray;
    }

    public int[] getIArray() {
        return fieldIArray;
    }

    public void setIArray(int[] fieldIArray) {
        this.fieldIArray = fieldIArray;
    }

    public long[] getJArray() {
        return fieldJArray;
    }

    public void setJArray(long[] fieldJArray) {
        this.fieldJArray = fieldJArray;
    }

    public float[] getFArray() {
        return fieldFArray;
    }

    public void setFArray(float[] fieldFArray) {
        this.fieldFArray = fieldFArray;
    }

    public double[] getDArray() {
        return fieldDArray;
    }

    public void setDArray(double[] fieldDArray) {
        this.fieldDArray = fieldDArray;
    }

    public Object[] getObjectArray() {
        return fieldObjectArray;
    }

    public void setObjectArray(Object[] fieldObjectArray) {
        this.fieldObjectArray = fieldObjectArray;
    }

    public Number[] getNumberArray() {
        return fieldNumberArray;
    }

    public void setNumberArray(Number[] fieldNumberArray) {
        this.fieldNumberArray = fieldNumberArray;
    }

    public Byte[] getByteArray() {
        return fieldByteArray;
    }

    public void setByteArray(Byte[] fieldByteArray) {
        this.fieldByteArray = fieldByteArray;
    }

    public Short[] getShortArray() {
        return fieldShortArray;
    }

    public void setShortArray(Short[] fieldShortArray) {
        this.fieldShortArray = fieldShortArray;
    }

    public Integer[] getIntegerArray() {
        return fieldIntegerArray;
    }

    public void setIntegerArray(Integer[] fieldIntegerArray) {
        this.fieldIntegerArray = fieldIntegerArray;
    }

    public Long[] getLongArray() {
        return fieldLongArray;
    }

    public void setLongArray(Long[] fieldLongArray) {
        this.fieldLongArray = fieldLongArray;
    }

    public Float[] getFloatArray() {
        return fieldFloatArray;
    }

    public void setFloatArray(Float[] fieldFloatArray) {
        this.fieldFloatArray = fieldFloatArray;
    }

    public Double[] getDoubleArray() {
        return fieldDoubleArray;
    }

    public void setDoubleArray(Double[] fieldDoubleArray) {
        this.fieldDoubleArray = fieldDoubleArray;
    }

    public Boolean[] getBooleanArray() {
        return fieldBooleanArray;
    }

    public void setBooleanArray(Boolean[] fieldBooleanArray) {
        this.fieldBooleanArray = fieldBooleanArray;
    }

    public Character[] getCharacterArray() {
        return fieldCharacterArray;
    }

    public void setCharacterArray(Character[] fieldCharacterArray) {
        this.fieldCharacterArray = fieldCharacterArray;
    }

    public CharSequence[] getCharSequenceArray() {
        return fieldCharSequenceArray;
    }

    public void setCharSequenceArray(CharSequence[] fieldCharSequenceArray) {
        this.fieldCharSequenceArray = fieldCharSequenceArray;
    }

    public String[] getStringArray() {
        return fieldStringArray;
    }

    public void setStringArray(String[] fieldStringArray) {
        this.fieldStringArray = fieldStringArray;
    }

    public Class[] getKlassArray() {
        return fieldKlassArray;
    }

    public void setKlassArray(Class[] fieldKlassArray) {
        this.fieldKlassArray = fieldKlassArray;
    }


    // === Static ============================================================
    //
    // Fields are all initialized to a value different from any value used in the tests.

    public static final boolean fieldStaticFinalZ = false;
    public static boolean fieldStaticZ = false;
    public static byte fieldStaticB = 42;
    public static char fieldStaticC = 42;
    public static short fieldStaticS = 42;
    public static int fieldStaticI = 42;
    public static long fieldStaticJ = 42;
    public static float fieldStaticF = 42;
    public static double fieldStaticD = 42;

    public static Object fieldStaticObject = "42";

    public static Number fieldStaticNumber = 42;
    public static Byte fieldStaticByte = 42;
    public static Short fieldStaticShort = 42;
    public static Integer fieldStaticInteger = 42;
    public static Long fieldStaticLong = 42L;
    public static Float fieldStaticFloat = 42f;
    public static Double fieldStaticDouble = 42d;
    public static Boolean fieldStaticBoolean = false;
    public static Character fieldStaticCharacter = 42;

    public static CharSequence fieldStaticCharSequence = "42";
    public static String fieldStaticString = "42";

    public static Class fieldStaticKlass = TestBasics.class;

    public static boolean[] fieldStaticZArray = {false, false};
    public static byte[] fieldStaticBArray = {42};
    public static char[] fieldStaticCArray = {42};
    public static short[] fieldStaticSArray = {42};
    public static int[] fieldStaticIArray = {42};
    public static long[] fieldStaticJArray = {42};
    public static float[] fieldStaticFArray = {42};
    public static double[] fieldStaticDArray = {42};

    public static Object[] fieldStaticObjectArray = {"42"};

    public static Number[] fieldStaticNumberArray = {42};
    public static Byte[] fieldStaticByteArray = {42};
    public static Short[] fieldStaticShortArray = {42};
    public static Integer[] fieldStaticIntegerArray = {42};
    public static Long[] fieldStaticLongArray = {42L};
    public static Float[] fieldStaticFloatArray = {42f};
    public static Double[] fieldStaticDoubleArray = {42d};
    public static Boolean[] fieldStaticBooleanArray = {false, false};
    public static Character[] fieldStaticCharacterArray = {42};

    public static CharSequence[] fieldStaticCharSequenceArray = {"42"};
    public static String[] fieldStaticStringArray = {"42"};

    public static Class[] fieldStaticKlassArray = {TestBasics.class};


    public static void staticNoArgs() {}
    public static void staticVarargs1(Object arg0, Object... args) {}

    public static boolean getStaticZ() {
        return fieldStaticZ;
    }

    public static void setStaticZ(boolean fieldStaticZ) {
        TestBasics.fieldStaticZ = fieldStaticZ;
    }

    public static byte getStaticB() {
        return fieldStaticB;
    }

    public static void setStaticB(byte fieldStaticB) {
        TestBasics.fieldStaticB = fieldStaticB;
    }

    public static char getStaticC() {
        return fieldStaticC;
    }

    public static void setStaticC(char fieldStaticC) {
        TestBasics.fieldStaticC = fieldStaticC;
    }

    public static short getStaticS() {
        return fieldStaticS;
    }

    public static void setStaticS(short fieldStaticS) {
        TestBasics.fieldStaticS = fieldStaticS;
    }

    public static int getStaticI() {
        return fieldStaticI;
    }

    public static void setStaticI(int fieldStaticI) {
        TestBasics.fieldStaticI = fieldStaticI;
    }

    public static long getStaticJ() {
        return fieldStaticJ;
    }

    public static void setStaticJ(long fieldStaticJ) {
        TestBasics.fieldStaticJ = fieldStaticJ;
    }

    public static float getStaticF() {
        return fieldStaticF;
    }

    public static void setStaticF(float fieldStaticF) {
        TestBasics.fieldStaticF = fieldStaticF;
    }

    public static double getStaticD() {
        return fieldStaticD;
    }

    public static void setStaticD(double fieldStaticD) {
        TestBasics.fieldStaticD = fieldStaticD;
    }

    public static Object getStaticObject() {
        return fieldStaticObject;
    }

    public static void setStaticObject(Object fieldStaticObject) {
        TestBasics.fieldStaticObject = fieldStaticObject;
    }

    public static Number getStaticNumber() {
        return fieldStaticNumber;
    }

    public static void setStaticNumber(Number fieldStaticNumber) {
        TestBasics.fieldStaticNumber = fieldStaticNumber;
    }

    public static Byte getStaticByte() {
        return fieldStaticByte;
    }

    public static void setStaticByte(Byte fieldStaticByte) {
        TestBasics.fieldStaticByte = fieldStaticByte;
    }

    public static Short getStaticShort() {
        return fieldStaticShort;
    }

    public static void setStaticShort(Short fieldStaticShort) {
        TestBasics.fieldStaticShort = fieldStaticShort;
    }

    public static Integer getStaticInteger() {
        return fieldStaticInteger;
    }

    public static void setStaticInteger(Integer fieldStaticInteger) {
        TestBasics.fieldStaticInteger = fieldStaticInteger;
    }

    public static Long getStaticLong() {
        return fieldStaticLong;
    }

    public static void setStaticLong(Long fieldStaticLong) {
        TestBasics.fieldStaticLong = fieldStaticLong;
    }

    public static Float getStaticFloat() {
        return fieldStaticFloat;
    }

    public static void setStaticFloat(Float fieldStaticFloat) {
        TestBasics.fieldStaticFloat = fieldStaticFloat;
    }

    public static Double getStaticDouble() {
        return fieldStaticDouble;
    }

    public static void setStaticDouble(Double fieldStaticDouble) {
        TestBasics.fieldStaticDouble = fieldStaticDouble;
    }

    public static Boolean getStaticBoolean() {
        return fieldStaticBoolean;
    }

    public static void setStaticBoolean(Boolean fieldStaticBoolean) {
        TestBasics.fieldStaticBoolean = fieldStaticBoolean;
    }

    public static Character getStaticCharacter() {
        return fieldStaticCharacter;
    }

    public static void setStaticCharacter(Character fieldStaticCharacter) {
        TestBasics.fieldStaticCharacter = fieldStaticCharacter;
    }

    public static CharSequence getStaticCharSequence() {
        return fieldStaticCharSequence;
    }

    public static void setStaticCharSequence(CharSequence fieldStaticCharSequence) {
        TestBasics.fieldStaticCharSequence = fieldStaticCharSequence;
    }

    public static String getStaticString() {
        return fieldStaticString;
    }

    public static void setStaticString(String fieldStaticString) {
        TestBasics.fieldStaticString = fieldStaticString;
    }

    public static Class getStaticKlass() {
        return fieldStaticKlass;
    }

    public static void setStaticKlass(Class fieldStaticKlass) {
        TestBasics.fieldStaticKlass = fieldStaticKlass;
    }


    public static boolean[] getStaticZArray() {
        return fieldStaticZArray;
    }

    public static void setStaticZArray(boolean[] fieldStaticZArray) {
        TestBasics.fieldStaticZArray = fieldStaticZArray;
    }

    public static byte[] getStaticBArray() {
        return fieldStaticBArray;
    }

    public static void setStaticBArray(byte[] fieldStaticBArray) {
        TestBasics.fieldStaticBArray = fieldStaticBArray;
    }

    public static char[] getStaticCArray() {
        return fieldStaticCArray;
    }

    public static void setStaticCArray(char[] fieldStaticCArray) {
        TestBasics.fieldStaticCArray = fieldStaticCArray;
    }

    public static short[] getStaticSArray() {
        return fieldStaticSArray;
    }

    public static void setStaticSArray(short[] fieldStaticSArray) {
        TestBasics.fieldStaticSArray = fieldStaticSArray;
    }

    public static int[] getStaticIArray() {
        return fieldStaticIArray;
    }

    public static void setStaticIArray(int[] fieldStaticIArray) {
        TestBasics.fieldStaticIArray = fieldStaticIArray;
    }

    public static long[] getStaticJArray() {
        return fieldStaticJArray;
    }

    public static void setStaticJArray(long[] fieldStaticJArray) {
        TestBasics.fieldStaticJArray = fieldStaticJArray;
    }

    public static float[] getStaticFArray() {
        return fieldStaticFArray;
    }

    public static void setStaticFArray(float[] fieldStaticFArray) {
        TestBasics.fieldStaticFArray = fieldStaticFArray;
    }

    public static double[] getStaticDArray() {
        return fieldStaticDArray;
    }

    public static void setStaticDArray(double[] fieldStaticDArray) {
        TestBasics.fieldStaticDArray = fieldStaticDArray;
    }

    public static Object[] getStaticObjectArray() {
        return fieldStaticObjectArray;
    }

    public static void setStaticObjectArray(Object[] fieldStaticObjectArray) {
        TestBasics.fieldStaticObjectArray = fieldStaticObjectArray;
    }

    public static Number[] getStaticNumberArray() {
        return fieldStaticNumberArray;
    }

    public static void setStaticNumberArray(Number[] fieldStaticNumberArray) {
        TestBasics.fieldStaticNumberArray = fieldStaticNumberArray;
    }

    public static Byte[] getStaticByteArray() {
        return fieldStaticByteArray;
    }

    public static void setStaticByteArray(Byte[] fieldStaticByteArray) {
        TestBasics.fieldStaticByteArray = fieldStaticByteArray;
    }

    public static Short[] getStaticShortArray() {
        return fieldStaticShortArray;
    }

    public static void setStaticShortArray(Short[] fieldStaticShortArray) {
        TestBasics.fieldStaticShortArray = fieldStaticShortArray;
    }

    public static Integer[] getStaticIntegerArray() {
        return fieldStaticIntegerArray;
    }

    public static void setStaticIntegerArray(Integer[] fieldStaticIntegerArray) {
        TestBasics.fieldStaticIntegerArray = fieldStaticIntegerArray;
    }

    public static Long[] getStaticLongArray() {
        return fieldStaticLongArray;
    }

    public static void setStaticLongArray(Long[] fieldStaticLongArray) {
        TestBasics.fieldStaticLongArray = fieldStaticLongArray;
    }

    public static Float[] getStaticFloatArray() {
        return fieldStaticFloatArray;
    }

    public static void setStaticFloatArray(Float[] fieldStaticFloatArray) {
        TestBasics.fieldStaticFloatArray = fieldStaticFloatArray;
    }

    public static Double[] getStaticDoubleArray() {
        return fieldStaticDoubleArray;
    }

    public static void setStaticDoubleArray(Double[] fieldStaticDoubleArray) {
        TestBasics.fieldStaticDoubleArray = fieldStaticDoubleArray;
    }

    public static Boolean[] getStaticBooleanArray() {
        return fieldStaticBooleanArray;
    }

    public static void setStaticBooleanArray(Boolean[] fieldStaticBooleanArray) {
        TestBasics.fieldStaticBooleanArray = fieldStaticBooleanArray;
    }

    public static Character[] getStaticCharacterArray() {
        return fieldStaticCharacterArray;
    }

    public static void setStaticCharacterArray(Character[] fieldStaticCharacterArray) {
        TestBasics.fieldStaticCharacterArray = fieldStaticCharacterArray;
    }

    public static CharSequence[] getStaticCharSequenceArray() {
        return fieldStaticCharSequenceArray;
    }

    public static void setStaticCharSequenceArray(CharSequence[] fieldStaticCharSequenceArray) {
        TestBasics.fieldStaticCharSequenceArray = fieldStaticCharSequenceArray;
    }

    public static String[] getStaticStringArray() {
        return fieldStaticStringArray;
    }

    public static void setStaticStringArray(String[] fieldStaticStringArray) {
        TestBasics.fieldStaticStringArray = fieldStaticStringArray;
    }

    public static Class[] getStaticKlassArray() {
        return fieldStaticKlassArray;
    }

    public static void setStaticKlassArray(Class[] fieldStaticKlassArray) {
        TestBasics.fieldStaticKlassArray = fieldStaticKlassArray;
    }

}
