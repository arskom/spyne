#!/bin/bash -x

2to3 -f next -w spyne/protocol/soap/soap11.py
2to3 -f except -f funcattrs -f metaclass -f print -w spyne
2to3 -f except -f funcattrs -f metaclass -f print -w examples

