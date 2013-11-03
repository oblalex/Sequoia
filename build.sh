#!/bin/bash

apt-get install python2.7-dev python-pip python-gtk2 libspeex-dev libportaudio2 libssl1.0.0 libssl-dev

pip install -r requirements.pip

wget http://people.csail.mit.edu/hubert/pyaudio/packages/python-pyaudio_0.2.7-1_i386.deb -O /tmp/python-pyaudio.deb
dpkg -i /tmp/python-pyaudio.deb

wget http://freenet.mcnabhosting.com/python/pySpeex/pySpeex.tar.gz -O /tmp/pySpeex.src.tar.gz
mkdir /tmp/pySpeex.src
tar -xvf /tmp/pySpeex.src.tar.gz -C /tmp/pySpeex.src
cd /tmp/pySpeex.src/python
sed -i 's/speex.h/speex\/speex.h/' speex.c
python setup.py build
python setup.py install
cd -

cd sequoia/gost
make && make clean
cd -
