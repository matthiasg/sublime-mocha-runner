import os
import sys
import pipes
import datetime
import threading

import sublime, sublime_plugin

class RunMochaCommand(sublime_plugin.EventListener):

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
        if not fn: return ''

        dirs = os.path.normpath(os.path.join(os.path.dirname(fn), name)).split(os.path.sep)
        
        f = dirs.pop()

        while dirs:
            joined = os.path.normpath(os.path.sep.join(dirs + [f]))
                    
            if os.path.exists(joined) and os.path.isdir(joined):                
                return os.path.normpath(os.path.sep.join(dirs))                
            else:
                dirs.pop()
            
    def run_mocha(self, folder, view):

        if self.worker_thread: return

        self.worker_thread = RunMochaWorker(folder, view)
        self.worker_thread.start()

        self.check_for_completion(view)

    def check_for_completion(self, view):

        if self.worker_thread.is_alive():
            view.set_status('Mocha', 'Testing ...')
            sublime.set_timeout(lambda: self.check_for_completion(view), 20)          
            return

        if self.worker_thread.result:
            self.output_result(view, self.worker_thread.result)

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

        return details;

    def output_message(self, view, message, details):

        view.set_status('Mocha', message )

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

    def __init__(self, success, lines):

        self.success = success
        self.lines = lines
        self.lines_ok = []
        self.lines_not_ok = []
        self.lines_other = []
        self.number_of_tests = 0
        self.number_of_successful_tests = 0
        self.number_of_failed_tests = 0

        for line in lines:
            print 'checking line:', line

            if line.startswith('ok'):
                self.lines_ok.append(line)
                self.number_of_tests = self.number_of_tests + 1
                self.number_of_successful_tests = self.number_of_successful_tests + 1
            elif line.startswith('not ok'):       
                self.lines_not_ok.append(line)
                self.number_of_tests = self.number_of_tests + 1
                self.number_of_failed_tests = self.number_of_failed_tests + 1
            else:
                self.lines_other.append(line)

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
            print "Unexpected error running mocha:", str(err)
            self.result = None
        except Exception, err:
            print "Unexpected error running mocha:", sys.exc_info()[0], str(err)
            self.result = None       


    def run_mocha(self, folder, view):

        os.chdir(folder)

        print "Starting tests in folder", folder
        
        result = getstatusoutput('mocha -R tap --compilers coffee:coffee-script')

        success = result[0]==0
        lines = result[1].splitlines()
        
        return MochaResult(success, lines)        

def getstatusoutput(cmd): 
        """Return (status, output) of executing cmd in a shell."""
        """This new implementation should work on all platforms."""
        import subprocess
        process = subprocess.Popen(cmd, shell=True, universal_newlines=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = str.join("", process.stdout.readlines()) 
        
        rc = process.wait()
        
        if rc is None:
            rc = 0

        output = pipes.quote(output)

        return rc, output

