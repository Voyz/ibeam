import sys
from subprocess import PIPE, Popen, CREATE_NEW_CONSOLE
from threading  import Thread
from queue import Queue, Empty

ON_POSIX = 'posix' in sys.builtin_module_names

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def run_subprocess(args, cwd):
    p = Popen(args, stdout=PIPE, cwd=cwd, bufsize=1, close_fds=ON_POSIX)
    q = Queue()
    t = Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True # thread dies with the program
    t.start()

    return p, q
