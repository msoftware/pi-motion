#!/bin/sh

DIR=`pwd`

while true; do
    echo
    echo "If you continue all existing text files will be deleted!"
    echo
    read -p "Do you wish to extract texts? (y/n)" yn
    case $yn in
        [Yy]* ) 
            mv sun.py sun.bak
            python -m i18n --root=$DIR --languages=en_US,de_DE extract
            mv sun.bak sun.py
            break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

exit


