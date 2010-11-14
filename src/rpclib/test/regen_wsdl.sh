#!/bin/sh

wget localhost:9753/?wsdl -qO - | tidy -xml -indent -wrap 0 > wsdl.xml 

