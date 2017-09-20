package com.chaquo.python;

import java.lang.reflect.*;
import java.util.*;

/** @deprecated */
public class Reflector {

    private final Class klass;
    private Map<String,Member> methods;               // We target Java 7, so we can't use
    private Map<String,List<Member>> multipleMethods; // java.lang.reflect.Executable.
    private Map<String,Field> fields;
    private Map<String,Class> classes;

    // FIXME explanation
    public static Reflector newInstance(Class klass) {
        return new Reflector(klass);
    }

    public Reflector(Class klass) {
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
        for (Method m : klass.getDeclaredMethods()) {
            if (isAccessible(m)) {
                loadMethod(m, m.getName());
            }
        }
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
        for (Field f : klass.getDeclaredFields()) {
            if (isAccessible(f)) {
                fields.put(f.getName(), f);
            }
        }
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
