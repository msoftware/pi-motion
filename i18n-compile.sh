#!/bin/sh

DIR=`pwd`
mv sun.py sun.bak
python -m i18n --root=$DIR --languages=en_US,de_DE compile
mv sun.bak sun.py

