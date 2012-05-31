#!/bin/bash 

export PYTHONPATH=../:../lib:$(find ../lib -name *.egg)

sphinx-apidoc -f -o "source/api" "../"

make html