# Manual user interface tests

## Auto-scroll
* Start Python unit tests. While tests are still running:
  * Confirm text auto-scrolls once it fills the screen.
  * Scroll up with a swipe. Text should stop auto-scrolling.
  * Scroll to bottom with a swipe. Text should resume auto-scrolling.
* Repeat using the scroll buttons in the toolbar.

## Scroll position
* Start Python console, and enter enough text to half fill the screen in portrait.
* Rotate screen back and forth. *Bottom* line scroll position should be maintained.
* Enter enough text to more than fill the screen in portrait.
* Rotate with scroll position at top, and in middle. *Top* line scroll position should be
  maintained.
* Show and hide the keyboard with scroll position at top, middle and bottom. Bottom or top line
  position should be maintained as described above.

## Stdin, stdout and stderr
* Start Python console.
* Enter some input, including some empty lines, and some errors.
  * Input text should appear in bold black.
  * Output text should appear in regular black.
  * Error text should appear in red.
* Scroll to top and enter another line. Output should auto-scroll back to bottom.
* Examine the Android log. Lines should be tagged "python.stdin" "python.stdout" or
  "python.stderr" as appropriate. Empty input lines should be included.

## Select, copy and paste
* Start Python console and enter a line. It should appear in bold.
* Select some of the line and rotate the screen. The selection should still be present.
* Copy the line and paste it into the input box. It should not appear in bold.

## Python console (REPL)
* Assign to a variable.
* Rotate the screen and evaluate the variable. The correct result should appear.
* Press back and open the console again. The previous output should still be there.
* Evaulate the variable. The correct result should appear.
* Type `exit()`. The word "Finished" should appear in blue, the keyboard should disappear, and
  the input box should be disabled.
* Rotate the screen. The previous output should still be there.
* Press back and open the console again. The previous output should have gone, and only the initial
  banner should be displayed.
* Evaluate the variable. A `NameError` should be displayed.

* Press back and open one of the other activities. Then kill the process using the button in
  the Logcat window (not the main toolbar). The main menu should reappear.
* Open the console again. The previous output should have gone, and only the initial banner should
  be displayed.

* Enter `context.getPackageName()`. The result should be `com.chaquo.python.demo3`.

* Enter a partial expression with an unclosed parenthesis. The "..." prompt should appear.
* Rotate the screen and complete the expression. The correct result should appear.

* Use the `print` function to print a non-ASCII Latin-1 character (e.g. "é"), and a non-Latin-1
  character (e.g. "√"). They should be output correctly both on screen and in the Android log.

* Enter the following, and rotate the screen while it runs. No numbers should be missing, and
  auto-scrolling should not stop.
  ```
  from time import sleep
  for i in range(50): print(i); sleep(0.1)
  ```

