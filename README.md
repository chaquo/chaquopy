# Introduction

Copyright (c) 2018 Chaquo Ltd

This repository contains the following components:

* `product` contains Chaquopy itself.
* `target` contains build processes for Python and its dependencies.
* `server/pypi` contains build processes for third-party Python packages.

The open-source demo apps are contained in separate repositories available at [https://github.com/chaquo/].


# Deployment

The artifacts produced by the `product` and `target` builds should be deployed to a Maven
repository similar to the [official Chaquopy one](https://chaquo.com/maven/). The repository is
simply a directory structure, which can be placed either on the local machine or on a
webserver.

Arrange the files similarly to this:

    maven
    └── com
        └── chaquo
            └── python
                ├── gradle
                │   └── 3.3.1
                │       ├── gradle-3.3.1.jar
                │       └── gradle-3.3.1.pom
                └── target
                    └── 3.6.5-4
                        ├── target-3.6.5-4-armeabi-v7a.zip
                        ├── target-3.6.5-4-stdlib.zip
                        ├── target-3.6.5-4-stdlib-pyc.zip
                        └── target-3.6.5-4-x86.zip

Now, to use this repository to build an app, follow the standard [Chaquopy setup
instructions](https://chaquo.com/chaquopy/doc/current/android.html#basic-setup), but replace
the URL https://chaquo.com/maven/ with the URL or local path of your own repository.
