#!/bin/sh -x

# The "boundary" string here must match with the one in the request body
# (typically the first line of the request body)

# The "start" string is similarly the content id of the first mime part
# it is currently ignored by the MtoM parser

curl -X POST \
    -H 'Content-Type: multipart/related; type="application/xop+xml"; '`
       `'boundary="uuid:2e53e161-b47f-444a-b594-eb6b72e76997"; '`
       `'start="<root.message@cxf.apache.org>"; '`
       `'start-info="application/soap+xml"; '`
       `'action="sendDocument"' \
    --data-binary @request.txt \
    http://localhost:8000
