sublime-mocha-runner
====================

NOTE: node.js under windows has a bug where it does not always flush console.log output before exiting.
This is most prominent when redirecting to another file or process (which is what mocha-runner does).
Therefore the output sometimes screws up especially it is the reason the stack trace does not appear on errors.
Ticket: https://github.com/joyent/node/issues/3584

Whenever a file is saved it searches the directory tree upwards for a test folder. When one is found it runs mocha.

The runner writes success and a timestamp into the status bar of the currently saved view. When mocha detects failures
it writes all failed tests TAP style to a new output view.

There are no settings it disable it yet and ALWAYS runs mocha whenever a folder named test is detected.
This should not cause any problems though.

NOTE: The program under test should not output anything to the console. This would screw up the TAP output required for parsing and most likely also the tests.

