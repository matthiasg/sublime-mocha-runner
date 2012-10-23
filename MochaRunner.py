import os
import sys
import pipes
import datetime
import threading
import subprocess
import traceback

import sublime
import sublime_plugin


class RunMochaCommand(sublime_plugin.EventListener):

    TEST_TIMEOUT_IN_SECONDS = 10

    worker_thread = None
    description = "Runs Mocha on save"

    def on_post_save(self, view):

        folder = self.find_folder(view, 'test')

        if not folder:
            print 'No tests found. Not running mocha.'
        else:
            self.run_mocha(folder, view)

    def find_folder(self, view, name):

        fn = view.file_name()
        if not fn:
            return ''

        dirs = os.path.normpath(os.path.join(os.path.dirname(fn), name)).split(os.path.sep)
        f = dirs.pop()

        while dirs:
            joined = os.path.normpath(os.path.sep.join(dirs + [f]))

            if os.path.exists(joined) and os.path.isdir(joined):
                return os.path.normpath(os.path.sep.join(dirs))
            else:
                dirs.pop()

    def run_mocha(self, folder, view):

        if self.worker_thread:
            return

        self.worker_started = datetime.datetime.now()

        self.worker_thread = RunMochaWorker(folder, view)
        self.worker_thread.start()

        self.check_for_completion(view)

    def check_for_completion(self, view):

        runningTime = datetime.datetime.now() - self.worker_started

        if self.worker_thread.is_alive():
            view.set_status('Mocha', 'Testing ... ' + str(runningTime.seconds) + 's')

            if runningTime.seconds < self.TEST_TIMEOUT_IN_SECONDS:
                sublime.set_timeout(lambda: self.check_for_completion(view), 20)
            else:
                self.worker_thread.stop()

            return

        if self.worker_thread.result:
            self.output_result(view, self.worker_thread.result)

        self.worker_started = None
        self.worker_thread = None

    def output_result(self, view, result):

        message = self.build_status_message(result)
        details = self.build_details(result)

        self.output_message(view, message, details)

        if result.success:
            self.hide_output_panel(view)
        else:
            self.show_output_panel(view)

    def build_status_message(self, result):

        if result.success:
            message = "SUCCESS"
        else:
            message = "FAILED"

        message = self.append_test_info(message, result)
        message = self.append_timestamp(message)

        return message

    def append_test_info(self, message, result):

        return message + " - OK #{0} FAIL #{1} TOTAL {2}".format(
                result.number_of_successful_tests,
                result.number_of_failed_tests,
                result.number_of_tests)

    def append_timestamp(self, text):

        today = datetime.datetime.now()
        time = today.strftime('%H:%M:%S')

        return text + " - " + time + "\n"

    def build_details(self, result):

        details = ""

        for line in result.lines_not_ok:
            details = details + line + "\n"

        if not result.success:
            details = details + "ERROR:\n"

        for errline in result.errlines:
            details = details + errline + "\n"

        return details

    def output_message(self, view, message, details):

        view.set_status('Mocha', message)

        out = view.window().get_output_panel('run_mocha')
        edit = out.begin_edit()

        out.erase(edit, sublime.Region(0, out.size()))

        out.insert(edit, out.size(), message)
        out.insert(edit, out.size(), details)

        out.show(out.size())
        out.end_edit(edit)

    def show_output_panel(self, view):
        self.run_panel_command(view, 'show_panel')

    def hide_output_panel(self, view):
        self.run_panel_command(view, 'hide_panel')

    def run_panel_command(self, view, command):
        view.window().run_command(command, {'panel': 'output.run_mocha'})


class MochaResult:

    def __init__(self, lines, errlines):

        self.success = True
        self.lines = lines
        self.errlines = errlines
        self.lines_ok = []
        self.lines_not_ok = []
        self.lines_other = []
        self.number_of_tests = 0
        self.number_of_successful_tests = 0
        self.number_of_failed_tests = 0

        if lines is not None:
            for line in lines:

                if line.startswith('ok'):
                    self.lines_ok.append(line)
                    self.number_of_tests = self.number_of_tests + 1
                    self.number_of_successful_tests = self.number_of_successful_tests + 1
                elif line.startswith('not ok'):
                    self.lines_not_ok.append(line)
                    self.number_of_tests = self.number_of_tests + 1
                    self.number_of_failed_tests = self.number_of_failed_tests + 1
                    self.success = False
                else:
                    self.lines_other.append(line)

        if errlines is not None and len(self.errlines) > 0:
            self.success = False


class RunMochaWorker(threading.Thread):

    def __init__(self, folder, view):

        self.folder = folder
        self.view = view
        self.result = None

        threading.Thread.__init__(self)

    def run(self):

        try:
            self.result = self.run_mocha(self.folder, self.view)
        except RuntimeError, err:
            print "Unexpected error running mocha:"
            traceback.print_tb(sys.last_traceback)
            self.result = None
        except Exception, err:
            print "Unexpected error running mocha:", sys.exc_info()[0], str(err)
            traceback.print_tb(sys.last_traceback)
            self.result = None

    def stop(self):

        if self.process:
            self.process.terminate()

        self.join()

    def run_mocha(self, folder, view):

        os.chdir(folder)

        print "Starting tests in folder", folder

        self.process = self.createProcess('mocha -R tap --compilers coffee:coffee-script')
        result = self.waitForProcess(self.process)

        lines = result[0].splitlines()
        errlines = result[1].splitlines()

        return MochaResult(lines, errlines)

    def createProcess(self, cmd):
        return subprocess.Popen(cmd, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def waitForProcess(self, process):

        stdoutdata, stderrdata = process.communicate()

        stdoutput = self.quote(stdoutdata)
        erroutput = self.quote(stderrdata)

        return stdoutput, erroutput

    def quote(self, str):
        if str is None:
            return ''
        else:
            return pipes.quote(str)
