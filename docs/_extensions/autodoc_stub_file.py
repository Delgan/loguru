"""
Small Sphinx extension intended to generate documentation for stub files.

It retrieves only the docstrings of "loguru/__init__.pyi", hence avoiding possible errors (caused by
missing imports or forward references). The stub file is loaded as a dummy module which contains
only the top-level docstring. All the formatting can therefore be handled by the "autodoc"
extension, which permits cross-reference.

The docstring of the stub file should list the available type hints and add short explanation of
their usage.

Warning: for some reason, the docs NEEDS to be re-generated for changes in the stub file to be taken
into account: ``make clean && make html``.
"""
import os
import sys
import types


def get_module_docstring(filepath):
    with open(filepath) as file:
        source = file.read()

    co = compile(source, filepath, "exec")

    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None

    return docstring


def setup(app):
    module_name = "autodoc_stub_file.loguru"
    stub_path = os.path.join("..", "loguru", "__init__.pyi")
    docstring = get_module_docstring(stub_path)
    module = types.ModuleType(module_name, docstring)
    sys.modules[module_name] = module
