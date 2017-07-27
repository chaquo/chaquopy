package com.chaquo.python;

import java.io.*;

public class TestArray {

	public static boolean methodParamsMatrixI(int[][] x) {
		if (x.length != 3 || x[0].length != 3)
			return false;
		return (x[0][0] == 1 && x[0][1] == 2 && x[1][2] == 6);
	}
	public static int[][] methodReturnMatrixI() {
        return new int[][]{{1,2,3},
                          {4,5,6},
                          {7,8,9}};
	}

	public static Object object;
    public static Serializable serializable;
    public static Cloneable cloneable;
    public static Closeable closeable;

}
