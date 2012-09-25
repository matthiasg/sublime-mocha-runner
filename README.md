sublime-mocha-runner
====================

Whenever a file is saved it searches the directory tree upwards for a test folder. When one is found it runs mocha.

The runner writes success and a timestamp into the status bar of the currently saved view. When mocha detects failures
it writes all failed tests TAP style to a new output view.

There are no settings it disable it yet and ALWAYS runs mocha whenever a folder named test is detected.
This should not cause any problems though.

NOTE: The program under test should not output anything to the console. This would screw up the TAP output required for parsing and most likely also the tests.