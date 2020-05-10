package com.chaquo.python;

import java.lang.reflect.*;
import java.util.*;

/** @deprecated */
public class Reflector {

    private final Class<?> klass;
    private Map<String,Member> methods;               // We target Java 7, so we can't use
    private Map<String,List<Member>> multipleMethods; // java.lang.reflect.Executable.
    private Map<String,Field> fields;
    private Map<String,Class> classes;

    private static Map<Class, Reflector> instances = new HashMap<>();

    public static Reflector getInstance(Class klass) {
        Reflector reflector = instances.get(klass);
        if (reflector != null) {
            return reflector;
        }
        reflector = new Reflector(klass);
        instances.put(klass, reflector);
        return reflector;
    }

    private Reflector(Class klass) {
        this.klass = klass;
    }

    public synchronized String[] dir() {
        if (methods == null) loadMethods();
        if (fields == null) loadFields();
        if (classes == null) loadClasses();
        Set<String> names = new HashSet<>();
        names.addAll(methods.keySet());
        names.addAll(multipleMethods.keySet());
        names.addAll(fields.keySet());
        names.addAll(classes.keySet());
        return names.toArray(new String[names.size()]);
    }

    public synchronized Member[] getMethods(String name) {
        if (methods == null) loadMethods();
        List<Member> list = multipleMethods.get(name);
        if (list != null) {
            return list.toArray(new Member[list.size()]);
        }
        Member method = methods.get(name);
        if (method != null) {
            return new Member[] { method };
        }
        return null;
    }

    private void loadMethods() {
        methods = new HashMap<>();
        multipleMethods = new HashMap<>();
        for (Constructor c : klass.getDeclaredConstructors()) {
            if (isAccessible(c)) {
                loadMethod(c, "<init>");
            }
        }
        for (Method m : getDeclaredMethods()) {
            if (isAccessible(m)) {
                loadMethod(m, m.getName());
            }
        }
    }

    private Collection<Method> getDeclaredMethods() {
        try {
            return Arrays.asList(klass.getDeclaredMethods());
        } catch (NoClassDefFoundError ignored) {}

        // On Android, getDeclaredMethods fails if any method signature refers to a class that
        // cannot be loaded
        // (https://android.googlesource.com/platform/libcore/+/refs/tags/android-5.0.0_r7/libart/src/main/java/java/lang/Class.java#771).
        // I don't know any perfect workaround for this, but there are a few ways we can
        // discover at least some of the methods.
        Set<Method> result = new HashSet<>();

        // Discover public methods: only works on API level 21 and higher.
        try {
            for (Method m : klass.getMethods()) {
                if (m.getDeclaringClass() == klass) {
                    try {
                        m.getReturnType();
                        m.getParameterTypes();
                        result.add(m);
                    } catch (NoClassDefFoundError ignored) {}
                }
            }
        } catch (NoClassDefFoundError ignored) {}

        // Discover inherited methods overridden by this class.
        for (Class c = klass.getSuperclass(); c != null; c = c.getSuperclass()) {
            for (Method inherited : Reflector.getInstance(c).getDeclaredMethods()) {
                try {
                    result.add(klass.getDeclaredMethod(inherited.getName(),
                                                       inherited.getParameterTypes()));
                } catch (NoSuchMethodException ignored) {}
            }
        }

        return result;
    }

    private void loadMethod(Member m, String name) {
        List<Member> list;
        Member mExisting = methods.remove(name);
        if (mExisting != null) {
            list = new ArrayList<>();
            list.add(mExisting);
            list.add(m);
            multipleMethods.put(name, list);
        } else if ((list = multipleMethods.get(name)) != null) {
            list.add(m);
        } else {
            methods.put(name, m);
        }
    }

    public synchronized Field getField(String name) {
        if (fields == null) loadFields();
        return fields.get(name);
    }

    private void loadFields() {
        fields = new HashMap<>();
        for (Field f : getDeclaredFields()) {
            if (isAccessible(f)) {
                fields.put(f.getName(), f);
            }
        }
    }

    private Collection<Field> getDeclaredFields() {
        try {
            return Arrays.asList(klass.getDeclaredFields());
        } catch (NoClassDefFoundError ignored) {}

        // See comment in getDeclaredMethods.
        Set<Field> result = new HashSet<>();

        // Discover public fields: this doesn't work on any version of Android as far as I know,
        // but we might as well keep it in case that changes.
        try {
            for (Field f : klass.getFields()) {
                if (f.getDeclaringClass() == klass) {
                    try {
                        f.getType();
                        result.add(f);
                    } catch (NoClassDefFoundError ignored) {}
                }
            }
        } catch (NoClassDefFoundError ignored) {}

        return result;
    }

    public synchronized Class getNestedClass(String name) {
        if (classes == null) loadClasses();
        return classes.get(name);
    }

    private void loadClasses() {
        classes = new HashMap<>();
        for (Class k : klass.getDeclaredClasses()) {
            if (isAccessible(k.getModifiers())) {
                String simpleName = k.getSimpleName();
                if (simpleName.isEmpty()) continue;   // Anonymous class
                classes.put(simpleName, k);
            }
        }
    }

    private boolean isAccessible(Member m) {
        if (! isAccessible(m.getModifiers())) return false;

        // Where a method override has identical parameter types but a covariant (i.e
        // subclassed) return type, the JVM will not consider it to be an override. So the
        // compiler generates a synthetic "bridge" method with the original return type.
        if (m.isSynthetic()) return false;

        return true;
    }

    // Protected members need to be accessible to static proxy classes, but we can't practically do
    // that without making them accessible everywhere. Technically package members should be
    // accessible as well if the static proxy is generated in the same package, but we'll leave
    // that for now.
    private boolean isAccessible(int modifiers) {
        return (modifiers & (Modifier.PUBLIC + Modifier.PROTECTED)) != 0;
    }

}
