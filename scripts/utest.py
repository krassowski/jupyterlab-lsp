""" run python unit tests with pytest"""
import sys

import pytest


def run_tests():
    """actually run the tests"""
    list(sys.argv[1:])

    return pytest.main()


if __name__ == "__main__":
    sys.exit(run_tests())
