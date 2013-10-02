#!/bin/bash

CDIR=`pwd`
wget --no-check-certificate http://freenet.mcnabhosting.com/python/pySpeex/pySpeex.tar.gz -O /tmp/pySpeex.src.tar.gz
mkdir /tmp/pySpeex.src
tar -xvf /tmp/pySpeex.src.tar.gz -C /tmp/pySpeex.src
cd /tmp/pySpeex.src/python
sed -i 's/speex.h/speex\/speex.h/' speex.c
python setup.py build
python setup.py install
cd $CDIR"/sequoia/gost"
make && make clean
cd $CDIR

