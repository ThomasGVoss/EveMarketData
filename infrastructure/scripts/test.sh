#! /bin/bash

source .venv/Scripts/activate

pushd src
pip install virtualenv
#virtualenv .venv
pip install -e ".[test]"

# Run the tests
pytest ../tests/

# Run the tests and generate a coverage report - or rather not, because the tests are not yet implemented
# coverage run -m pytest tests/

popd