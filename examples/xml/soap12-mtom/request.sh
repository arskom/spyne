#!/bin/sh -x

curl -X POST \
    -H 'Content-Type: multipart/related; type="application/xop+xml"; '`
       `'boundary="uuid:2e53e161-b47f-444a-b594-eb6b72e76997"; '`
       `'start="<root.message@cxf.apache.org>"; '`
       `'start-info="application/soap+xml"; '`
       `'action="sendDocument"' \
    --data-binary @request.txt \
    http://localhost:8000
