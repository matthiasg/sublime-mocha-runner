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

        out = view.window().get_output_panel('run_mocha')                
        edit = out.begin_edit()
        
        out.erase(edit, sublime.Region(0, out.size()))
        
        today = datetime.datetime.now()
        time = today.strftime('%H:%M:%S')

        if result.success:
            message = "SUCCESS - " + time + "\n"
            out.insert(edit, out.size(), message)
            view.set_status('Mocha', message )
        else:
            message = "FAILED - " + time + "\n"
            out.insert(edit, out.size(), message)
            view.set_status('Mocha', message )
            

        for line in result.lines_not_ok:
            out.insert(edit, out.size(), line + "\n")

        out.show(out.size())        
        out.end_edit(edit)
        
        if result.success:
            view.window().run_command('hide_panel', {'panel': 'output.run_mocha'})
        else:
            view.window().run_command('show_panel', {'panel': 'output.run_mocha'})
       
class MochaResult:

    def __init__(self, success, lines):

        self.success = success
        self.lines = lines
        self.lines_ok = []
        self.lines_not_ok = []
        self.lines_other = []

        for line in lines:

            if line.startswith('ok'):
                self.lines_ok.append(line)
            elif line.startswith('not ok'):       
                self.lines_not_ok.append(line)
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

        print "Starting in folder", folder
        print "Running with view", view
        
        result = getstatusoutput('mocha -R tap --compilers coffee:coffee-script')

        success = result[0]==0
        lines = result[1].splitlines()
        
        return MochaResult(success, lines)        

def getstatusoutput(cmd): 
        """Return (status, output) of executing cmd in a shell."""
        """This new implementation should work on all platforms."""
        import subprocess
        pipe = subprocess.Popen(cmd, shell=True, universal_newlines=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = str.join("", pipe.stdout.readlines()) 
        sts = pipe.wait()
        if sts is None:
            sts = 0

        output = pipes.quote(output)
        return sts, output

