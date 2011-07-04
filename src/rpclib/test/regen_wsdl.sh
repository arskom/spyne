#!/bin/sh

wget localhost:9753/?wsdl -qO - | sort_wsdl | tidy -xml -indent -wrap 0 --sort-attributes alpha | sed -e "s/ xmlns:/\n                  xmlns:/g" > wsdl.xml

