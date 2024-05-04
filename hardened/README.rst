Loguru hardened
---------------

Loguru hardened is a release of loguru which has small patches to make the default use more secure (and less developer friendly).

The following changes make loguru-hardened different:

- Use serialize by default to mitigate possible injection of newlines by logging data injected by malicious user.
  See https://huntr.com/bounties/73ebb08a-0415-41be-b9b0-0cea067f6771
- Disable diagnose by default, to keep context information from leaking into the logs.
