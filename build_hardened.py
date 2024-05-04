import os
import shutil
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


def replace_with_hardened_files():
    """Replace the loguru files with hardened versions"""
    # Walk hardened folder and copy files to loguru folder
    for root, _, files in os.walk("hardened"):
        for file in files:
            assert os.path.isfile(os.path.join("loguru", file))
            # Copy file to loguru folder
            shutil.copy(os.path.join(root, file), os.path.join("loguru", file))


def main():
    """Update the setup.py file for logoru-hardened

    - copy hardened files in place,
    - test
    - build
    - git checkout changes
    """
    update_setup_py()
    replace_with_hardened_files()
    tox_test_result = subprocess.run(["tox", "-e", "tests"])
    tox_test_result.check_returncode()
    build_result = subprocess.run(["python", "-m", "build"])
    build_result.check_returncode()
    git_checkout_result = subprocess.run(["git", "checkout", "loguru", "setup.py"])
    git_checkout_result.check_returncode()


if __name__ == "__main__":
    main()
