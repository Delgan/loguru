import os
import sys
import sysconfig

usersite = os.path.abspath(os.path.join(os.path.dirname(__file__), "usersite"))
sys.path.append(usersite)
sysconfig._INSTALL_SCHEMES["posix_user"]["purelib"] = usersite
