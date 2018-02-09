# Manual user interface tests

## Auto-scrolling
* Start "Python unit tests". Text should auto-scroll once it reaches bottom.
* While tests are still running:
  * Scroll up. Text should stop auto-scrolling.
  * Scroll to bottom. Text should resume auto-scrolling.

## Stderr
* Run "Python unit tests".
* Output text should appear in black, except for "Hello stderr" near the start, and some
  exception traces near the end, which should be red.
* Examine the Android log. Lines should be tagged "python.stdout" or "python.stderr" as
  appropriate.

## Stdin
* Start "Python console".
* Enter some lines to make the text start scrolling. All input text should appear in bold.
* Scroll to top and enter another line. Output should auto-scroll back to bottom.
* Examine the Android log. Lines should be tagged "python.stdout" or "python.stdin" as
  appropriate.

## Copy and paste
* Start "Python console" and enter a line. It should appear in bold.
* Copy the line and paste it into the input box. It should not appear in bold.



On rotation or keyboard show/hide, should maintain top position if possible, unless scrolled to
bottom, in which case should maintain bottom position. Test at top, middle and bottom.

Rotation should not interrupt or restart run.

Select and copy should not leave behind invisible cursor.

Console local variables and scrollback should survive a rotation and a back/forward.

Console exit() should print [Finished] in blue and disable stdin. Rotation should then maintain
scrollback, but back/forward should reset.

Remove REPL special case. Likewise for unit tests, pressing back during run should allow
remainder of run to be captured invisibly. Only a back *after* finished will reset.


print Unicode (should be non-Latin-1 also)
