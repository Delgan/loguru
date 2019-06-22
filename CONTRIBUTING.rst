Thank you for considering improving `Loguru`, any contribution is much welcome!

.. _minimal reproducible example: https://stackoverflow.com/help/mcve
.. _open a new issue: https://github.com/Delgan/loguru/issues/new
.. _open a pull request: https://github.com/Delgan/loguru/compare
.. _PEP 8: https://www.python.org/dev/peps/pep-0008/
.. _Loguru: https://github.com/Delgan/loguru

Asking questions
----------------

If you have any question about `Loguru`, if you are seeking for help, or if you would like to suggest a new feature, you are encouraged to `open a new issue`_ so we can discuss it. Bringing new ideas and pointing out elements needing clarification allows to make this library always better!


Reporting a bug
---------------

If you encountered an unexpected behavior using `Loguru`, please `open a new issue`_ and describe the problem you have spotted. Be as specific as possible in the description of the trouble so we can easily analyse it and quickly fix it.

An ideal bug report includes:

* The Python version you are using
* The `Loguru` version you are using (you can find it with ``print(loguru.__version__)``)
* Your operating system name and version (Linux, MacOS, Windows)
* Your development environment and local setup (IDE, Terminal, project context, any relevant information that could be useful)
* Some `minimal reproducible example`_


Implementing changes
--------------------

If you are willing to enhance `Loguru` by implementing non-trivial changes, please `open a new issue`_ first to keep a reference about why such modifications are made (and potentially avoid unneeded work). Then, the workflow would look as follows:

1. Fork the `Loguru`_ project from GitHub
2. Clone the repository locally::

    $ git clone git@github.com:your_name_here/loguru.git
    $ cd loguru

3. Activate your virtual environment::

    $ python -m virtualenv env
    $ source env/bin/activate

4. Create a new branch from ``master``::

    $ git checkout master
    $ git branch fix_bug
    $ git checkout fix_bug

5. Install `Loguru` in development mode::

    $ pip install -e .[dev]

6. Implement the modifications wished. During the process of development, honor `PEP 8`_ as much as possible.
7. Add unit tests (don't hesitate to be exhaustive!) and ensure none are failing using::

    $ tox

8. Remember to update documentation if required
9. Update the ``CHANGELOG.rst`` file with what you improved
10. ``add`` and ``commit`` your changes, ``rebase`` your branch on ``master``, ``push`` your local project::

    $ git add .
    $ git commit -m 'Add succinct explanation of what changed'
    $ git rebase master
    $ git push origin fix_bug

11. Finally, `open a pull request`_ before getting it merged!
