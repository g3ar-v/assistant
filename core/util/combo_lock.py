from threading import Lock
from fasteners.process_lock import InterProcessLock
from os.path import exists
from os import chmod


class ComboLock:
    """ A combined process and thread lock.

    Args:
        path (str): path to the lockfile for the lock
    """
    def __init__(self, path):
        # Create lock file if it doesn't exist and set permissions for
        # all users to lock/unlock
        if not exists(path):
            f = open(path, 'w+')
            f.close()
            chmod(path, 0o777)
        self.plock = InterProcessLock(path)
        self.tlock = Lock()

    def acquire(self, blocking=True):
        """ Acquire lock, locks thread and process lock.

        Args:
            blocking(bool): Set's blocking mode of acquire operation.
                            Default True.

        Returns: True if lock succeeded otherwise False
        """
        if not blocking:
            # Lock thread
            tlocked = self.tlock.acquire(blocking=False)
            if not tlocked:
                return False
            # Lock process
            plocked = self.plock.acquire(blocking=False)
            if not plocked:
                # Release thread lock if process couldn't be locked
                self.tlock.release()
                return False
        else:  # blocking, just wait and acquire ALL THE LOCKS!!!
            self.tlock.acquire()
            self.plock.acquire()
        return True

    def release(self):
        """ Release acquired lock. """
        self.plock.release()
        self.tlock.release()

    def __enter__(self):
        """ Context handler, acquires lock in blocking mode. """
        self.acquire()
        return self

    def __exit__(self, _type, value, traceback):
        """ Releases the lock. """
        self.release()
