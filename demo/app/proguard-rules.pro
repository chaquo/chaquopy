# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# Uncomment this to preserve the line number information for
# debugging stack traces.
-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile

# Android UI demo
-keep class chaquopy.demo.ui_demo.** { *; }
-keep class androidx.appcompat.app.** { *; }
-keep class androidx.core.app.** { *; }
-keep class androidx.fragment.app.** { *; }
-keep class androidx.preference.** { *; }

# Java unit tests
-keep class com.chaquo.java.** { *; }
-keep class org.junit.** { *; }

# Python unit tests
-keep class package1.** { *; }  # TestImport
-keepattributes Exceptions  # TestProxy.test_exception
-keep class kotlin.jvm.functions.** { *; }           # TestReflect.test_call_kotlin
-keep class kotlin.jvm.internal.FunctionBase { *; }  #
-keep class kotlin.reflect.KAnnotatedElement { *; }  #
-keep class chaquopy.test.static_proxy.** { *; }  # TestStaticProxy
