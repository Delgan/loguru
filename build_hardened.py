#!/usr/bin/env python
"""
Loguru hardened
---------------

Loguru hardened is a release of loguru which has small patches that
make the default use more secure (and less developer friendly).

The following changes make loguru-hardened different:

- Use serialize by default to mitigate possible injection of newlines
  when logging data injected by malicious user.
  See https://huntr.com/bounties/73ebb08a-0415-41be-b9b0-0cea067f6771
- Disable diagnose by default, to keep context information from leaking into the logs.
"""
import subprocess


def update_setup_py():
    """Update the setup.py file to replace loguru with loguru-hardened"""
    with open("setup.py", "r") as f:
        setup_py = f.read()

    # Replace loguru with loguru-hardened
    setup_py = setup_py.replace('name="loguru"', 'name="loguru-hardened"')

    # Write the updated setup.py file
    with open("setup.py", "w") as f:
        f.write(setup_py)


def update_defaults_py():
    """Set HARDENED_BUILD to True in _defaults.py"""
    defaults_py_path = "loguru/_defaults.py"
    with open(defaults_py_path, "r") as f:
        defaults_py = f.read()
    hardened_defaults = defaults_py.replace("HARDENED_BUILD = False", "HARDENED_BUILD = True")
    assert hardened_defaults != defaults_py
    with open(defaults_py_path, "w") as f:
        f.write(hardened_defaults)


def main():
    """Update the setup.py file for logoru-hardened

    - patch to become hardened:
        - setup.py
        - _defaults.py
    - test
    - build
    - git checkout changes
    """
    update_setup_py()
    update_defaults_py()
    tox_test_result = subprocess.run(["tox", "-e", "tests"])
    tox_test_result.check_returncode()
    build_result = subprocess.run(["python", "-m", "build"])
    build_result.check_returncode()
    git_checkout_result = subprocess.run(["git", "checkout", "loguru", "setup.py"])
    git_checkout_result.check_returncode()


if __name__ == "__main__":
    main()
