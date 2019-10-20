import os

if os.name == "nt":
    import win32_setctime

    def get_ctime(filepath):
        return os.stat(filepath).st_ctime

    def set_ctime(filepath, timestamp):
        if win32_setctime.SUPPORTED:
            win32_setctime.setctime(filepath, timestamp)


elif hasattr(os.stat_result, "st_birthtime"):

    def get_ctime(filepath):
        return os.stat(filepath).st_birthtime

    def set_ctime(filepath, timestamp):
        pass


else:

    def get_ctime(filepath):
        try:
            return float(os.getxattr(filepath, b"user.loguru_crtime"))
        except OSError:
            return os.stat(filepath).st_mtime

    def set_ctime(filepath, timestamp):
        try:
            os.setxattr(filepath, b"user.loguru_crtime", str(timestamp).encode("ascii"))
        except OSError:
            pass
