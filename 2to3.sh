#!/bin/bash -x

2to3 -f next -w src/rpclib/protocol/soap/soap11.py
2to3 -f except -f funcattrs -f metaclass -f print -w src/rpclib
2to3 -f except -f funcattrs -f metaclass -f print -w examples

