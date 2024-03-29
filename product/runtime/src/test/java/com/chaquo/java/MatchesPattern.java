package com.chaquo.java;

import org.hamcrest.Description;
import org.hamcrest.Matcher;
import org.hamcrest.TypeSafeMatcher;

import java.util.regex.Pattern;


/** Copied from Hamcrest 2, which doesn't interact well with JUnit 4 and ProGuard
 *  ("Missing class org.hamcrest.Factory"). */
public class MatchesPattern extends TypeSafeMatcher<String> {

    private final Pattern pattern;

    public MatchesPattern(Pattern pattern) {
        this.pattern = pattern;
    }

    @Override
    protected boolean matchesSafely(String item) {
        return pattern.matcher(item).matches();
    }

    @Override
    public void describeTo(Description description) {
        description.appendText("a string matching the pattern '" + pattern + "'");
    }

    /**
     * Creates a matcher of {@link java.lang.String} that matches when the examined string
     * exactly matches the given {@link java.util.regex.Pattern}.
     *
     * @param pattern
     *     the text pattern to match.
     * @return The matcher.
     */
    public static Matcher<String> matchesPattern(Pattern pattern) {
        return new MatchesPattern(pattern);
    }

    /**
     * Creates a matcher of {@link java.lang.String} that matches when the examined string
     * exactly matches the given regular expression, treated as a {@link java.util.regex.Pattern}.
     *
     * @param regex
     *     the regex to match.
     * @return The matcher.
     */
    public static Matcher<String> matchesPattern(String regex) {
        return new MatchesPattern(Pattern.compile(regex));
    }

}