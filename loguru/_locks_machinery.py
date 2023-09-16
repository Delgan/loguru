import os
import threading
import weakref

if not hasattr(os, "register_at_fork"):

    def create_logger_lock():
        return threading.Lock()

    def create_handler_lock():
        return threading.Lock()

    def create_queue_lock():
        return threading.Lock()

    def create_error_lock():
        return threading.Lock()

else:
    # Using "fork()" in a multi-threaded Python app is kind of deprecated. Although it can work most
    # of the time, it is not guaranteed to be safe because it doesn't respect the POSIX standard.
    # Still, we need to support it as it can be used by some users, therefore we need to take some
    # precautions. Additionally, Loguru itself makes use of threads when "enqueue=True"; it remains
    # to be decided whether we should drop compatibility with "fork()" ore re-implement the
    # feature using "multiprocessing" instead.
    #
    # Apart from the non compliance to standards, mixing threads and multiprocessing "fork" will
    # create problems if some important principles are not respected. The entire memory is copied to
    # the child process, so if a new process is created while a lock is in the "acquired" state, the
    # copied lock will also be in the "acquired" state in the newly started process, causing a
    # potential deadlock. This can occur if the process is forked by the main thread while there is
    # another thread using locks running in the background.
    #
    # A possible workaround to this problem consists of acquiring all locks before forking, and then
    # releasing them in the parent and child processes. This is what is done below using the
    # "os.register_at_fork()" function. This also ensures that the sinks are not interrupted during
    # execution and that the possible internal resources they use are not copied in an invalid
    # state.
    #
    # However, this technique requires attention to the order in which the locks are acquired. If a
    # function uses nested locks, it is crucial to acquire the "outer" lock before the "inner" lock.
    # For example, "Logger.remove()" acquires a Lock and then calls "Handler.stop()" which itself
    # acquires a second Lock. If a fork occurs between these two steps in a different thread, the
    # "acquire_locks()" function must not acquire the second Lock first, as this could lead to a
    # deadlock. For this reason, locks are identified by four different types representing their
    # intended use according to the current implementation of Loguru. This makes it possible to
    # guarantee their correct order of acquisition.
    #
    # Additionally, it is important to ensure that no new locks are created while forking is
    # occurring in a different thread. This can result in errors, such as changes in the set size
    # during iteration or attempts to release a lock that was not previously acquired. To address
    # this, a global "machinery_lock" is used.
    #
    # Special consideration must be paid to the registration of new locks, though. Creating a new
    # lock requires first acquiring the global lock. However, we stated above that the order of
    # acquisition of locks during a fork must be the same as the order of (nested) acquisition in
    # the code. This constraint implies that no lock should be created when another lock is already
    # in use. Consequently, the Logger must take care that all internal locks are created in
    # advance, outside the scope of any other lock, to ensure that the above measures are effective.
    #
    # Finally, usage of threading Condition can also cause problems. During a fork, the number of
    # current waiters is also copied to the child process. To prevent deadlocks, each Condition
    # instance must be re-created in the child process, and the inherited one must not be re-used.

    machinery_lock = threading.Lock()

    logger_locks = weakref.WeakSet()
    handler_locks = weakref.WeakSet()
    queue_locks = weakref.WeakSet()
    error_locks = weakref.WeakSet()

    def acquire_locks():
        machinery_lock.acquire()

        for lock in logger_locks:
            lock.acquire()

        for lock in handler_locks:
            lock.acquire()

        for lock in queue_locks:
            lock.acquire()

        for lock in error_locks:
            lock.acquire()

    def release_locks():
        for lock in error_locks:
            lock.release()

        for lock in queue_locks:
            lock.release()

        for lock in handler_locks:
            lock.release()

        for lock in logger_locks:
            lock.release()

        machinery_lock.release()

    os.register_at_fork(
        before=acquire_locks,
        after_in_parent=release_locks,
        after_in_child=release_locks,
    )

    def create_logger_lock():
        with machinery_lock:
            lock = threading.Lock()
            logger_locks.add(lock)
        return lock

    def create_handler_lock():
        with machinery_lock:
            lock = threading.Lock()
            handler_locks.add(lock)
        return lock

    def create_queue_lock():
        with machinery_lock:
            lock = threading.Lock()
            queue_locks.add(lock)
        return lock

    def create_error_lock():
        with machinery_lock:
            lock = threading.Lock()
            error_locks.add(lock)
        return lock
