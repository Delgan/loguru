.. _type-hints:

Type hints
==========

.. automodule:: autodoc_stub_file.loguru


See also: :ref:`type-hints-source`.

Mypy plugin
===========

**Loguru**, as a project, is `PEP484 <https://www.python.org/dev/peps/pep-0484/>` compatible and thus
exports type hints. However type hints are not everything. Therefore one can also use
`loguru-mypy <https://github.com/kornicameister/loguru-mypy>`.

Plugin can be installed seperately or as an extra for **Loguru** by
::

    pip install logoru[mypy]
