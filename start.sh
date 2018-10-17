#!/bin/sh
set -e

/usr/bin/dockerize -wait tcp://db:5432
/usr/bin/env ipython -i riptide.py data.txt
