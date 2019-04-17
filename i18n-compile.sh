#!/bin/sh

mv sun.py sun.bak
python -m i18n --root=/home/pi/pi-motion --languages=en_US,de_DE compile
mv sun.bak sun.py

