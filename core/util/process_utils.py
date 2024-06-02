import os
import signal
from threading import Thread
from time import sleep

import psutil


def kill_process_tree():
    pid = os.getpid()  # Get the current process ID
    try:
        # Send SIGTERM to the entire process group to ensure all processes are targeted
        os.killpg(os.getpgid(pid), signal.SIGKILL)
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            print(f"Forcefully terminating child PID {child.pid}")
            child.kill()  # Forcefully kill the child process immediately
        gone, still_alive = psutil.wait_procs(children, timeout=3)

        if still_alive:
            for child in still_alive:
                print(f"Child PID {child.pid} still alive, attempting another kill")
                child.kill()

        print(f"Forcefully terminating parent PID {pid}")
        parent.kill()  # Forcefully kill the parent process immediately
        parent.wait(3)  # Wait for the parent process to terminate
    except psutil.NoSuchProcess:
        print(f"Process {pid} does not exist or is already terminated")
    except psutil.AccessDenied:
        print(f"Permission denied to terminate some processes")


def create_daemon(target, args=(), kwargs=None):
    """Helper to quickly create and start a thread with daemon = True"""
    t = Thread(target=target, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t


def wait_for_exit_signal():
    """Blocks until KeyboardInterrupt is received."""
    try:
        while True:
            sleep(100)
    except KeyboardInterrupt:
        pass
