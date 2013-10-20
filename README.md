Sequoia
=======

Synopsis
--------

Secure voice conference for educational purposes. Control protocol is protected
by TLS, audio data are protected by bidirectioal GOST encryption. One key is
used for outcoming data, another is used for incoming data. Audio data are
compressed by Speex codec.

Mixing of audio channels is done on the server side.

Storing user's info is provided by using SQlite3 on the server side.

Installation
------------

TODO

Usage
-----

### Setting up server

#### Using root private key and certificate

You can use root private key and certificate provided by a certificate
authority or create your own.

Creating own **root private key**:

    openssl genrsa -out root_ca.key 2048

or protected with password:

    openssl genrsa -out root_ca.key 2048 -des3

Creating own self-signed **root certificate**:

    openssl req -x509 -new -nodes -key root_ca.key -days 1024 -out root_ca.crt

#### Creating server's private key and certificate

Server's private key and certificate can be created same way as for a regular
user.

Creating **server's private key**:

    openssl genrsa -out server.key 2048

Creating server's **certificate signing request**:

    openssl req -new -key server.key -out server.csr

Creating **server's root-signed certificate**:

    openssl x509 -req -in server.csr -CA root_ca.crt -CAkey root_ca.key -CAcreateserial -out server.crt -days 500

#### Initializing database

For server's work you need to initialize SQlite3 database. To do this you can
run

    sequoia/management/init_db.py --path=/path/to/sequoia/database.db

This will create empty database on the path you've specified. If '--path' key
is not specified then dabase will be created in the current directory and named
as 'sequoia.db'.

#### Registering user

To register a user you need to create a private key and certificate for him
just the same way as for server:

Creating **client's private key**:

    openssl genrsa -out client.key 2048

Creating client's **certificate signing request**:

    openssl req -new -key client.key -out client.csr

Creating **client's root-signed certificate**:

    openssl x509 -req -in client.csr -CA root_ca.crt -CAkey root_ca.key -CAcreateserial -out client.crt -days 500

Next step is to register user in the database and get 256-bit key pairs for
encrypting media with GOST:

    sequoia/management/register_user.py --nick=nickname --crt=/path/to/user/certificate.crt --db=/path/to/sequoia/database.db --out=/path/to/media.keys

This will register user with 'nickname' nickname in specified database. Serial
number of user's certificate will be used as login during authentication. The
result of registering will be JSON-file with key pairs for GOST. If 'out' key
is not specified then keys will be saved in the current directory and named
as 'media.keys'.

Running server
--------------

TODO

Running client
--------------

TODO
