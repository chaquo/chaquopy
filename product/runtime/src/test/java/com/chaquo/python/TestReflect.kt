@file:Suppress("unused")
package com.chaquo.python

class TestReflectKt {

    class Call(s: String) {
        @JvmField val s = "kt instance $s"
        fun getS() = s
        @JvmField val boundInstanceRef = ::getS

        companion object {
            @JvmField val anon = object : TestReflect.Call.Function<String, String> {
                override fun apply(s: String): String = "kt anon $s"
            }

            @JvmField val lamb = { s: String -> "kt lambda $s" }

            fun func(s: String) = "kt func $s"
            @JvmField val funcRef = ::func

            @JvmField val unboundInstanceRef = Call::getS
            @JvmField val constructorRef = ::Call
        }
    }
}