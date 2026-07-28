import atexit
import multiprocessing
import multiprocessing.managers
import os
import threading

# these get put in the environment so a spawned child process can find the parent's queue
ENV_HOST = "LOGURU_MP_HOST"
ENV_PORT = "LOGURU_MP_PORT"
ENV_KEY = "LOGURU_MP_KEY"
ENV_CATCH = "LOGURU_MP_CATCH"
STOP = "__STOP__"  # put this on the queue to kill the listener thread

_queue_holder = []


def _get_shared_queue():
    # module-level list acts as a slot
    if not _queue_holder:
        _queue_holder.append(multiprocessing.JoinableQueue())
    return _queue_holder[0]


class QueueManager(multiprocessing.managers.SyncManager):
    pass


QueueManager.register("get_queue", callable=_get_shared_queue)


def enable(core, context=None, catch=True):
    if core._mp_state is not None:
        return  # already on, don't start a second manager
    manager = QueueManager(address=("127.0.0.1", 0))
    manager.start()
    q = manager.get_queue()
    core._mp_state = {"manager": manager, "queue": q, "pid": os.getpid(), "catch": catch}
    t = threading.Thread(target=_listen, args=(core, q, catch), daemon=True)
    t.start()
    core._mp_state["thread"] = t
    # manager.address is (host,port)
    host, port = manager.address
    os.environ[ENV_HOST] = str(host)
    os.environ[ENV_PORT] = str(port)
    os.environ[ENV_KEY] = manager._authkey.hex()
    os.environ[ENV_CATCH] = "1" if catch else "0"
    atexit.register(disable, core)


def disable(core):
    state = core._mp_state
    if state is None:
        return
    if state["pid"] != os.getpid():
        return  # we're in a forked child that inherited this state,ignore
    state["queue"].put(STOP)
    state["thread"].join(timeout=5)
    state["manager"].shutdown()
    core._mp_state = None
    _queue_holder.clear()
    os.environ.pop(ENV_HOST, None)
    os.environ.pop(ENV_PORT, None)
    os.environ.pop(ENV_KEY, None)
    os.environ.pop(ENV_CATCH, None)


def _listen(core, q, catch):
    while True:
        item = q.get()
        if item == STOP:
            q.task_done()
            return
        record, level_id, from_decorator, raw = item
        try:
            for handler in core.handlers.values():
                handler.emit(record, level_id, from_decorator, raw, None)
        except Exception:
            if not catch:
                raise
        finally:
            q.task_done()


def check_if_child(core):
    if ENV_HOST in os.environ:
        core._mp_pending = True


def try_attach(core):
    # called at the top of every _log() call whose core has no queue yet this covers
    # spawn and fork
    state = core._mp_state
    if state is not None and state["pid"] == os.getpid():
        return  # this really is the owner process, nothing to attach to
    if core._mp_attempted:
        return
    if not (core._mp_pending or ENV_HOST in os.environ):
        return
    core._mp_attempted = True
    connect_child(core)


def connect_child(core):
    core._mp_pending = False
    host = os.environ.get(ENV_HOST)
    port = os.environ.get(ENV_PORT)
    key = os.environ.get(ENV_KEY)
    catch = os.environ.get(ENV_CATCH, "1") == "1"
    if not host:
        return
    manager = QueueManager(address=(host, int(port)), authkey=bytes.fromhex(key))
    try:
        manager.connect()
    except Exception:
        if not catch:
            raise
        return
    core._mp_queue = manager.get_queue()
    core._mp_catch = catch


def send(core, record, level_id, from_decorator, raw):
    try:
        core._mp_queue.put((record, level_id, from_decorator, raw))
    except Exception:
        if not core._mp_catch:
            raise


def flush(core):
    state = core._mp_state
    if state is None or state["pid"] != os.getpid():
        return  # not enabled, or we're a forked child, not the owner
    state["queue"].join()
