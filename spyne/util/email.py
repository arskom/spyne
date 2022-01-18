
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import getpass
import inspect
import traceback
import smtplib
import mimetypes

from socket import gethostname
from subprocess import Popen, PIPE

from email.utils import COMMASPACE, formatdate
from email import message_from_string
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.message import MIMEMessage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.nonmultipart import MIMENonMultipart
from email.encoders import encode_base64

from spyne.util import six


def email_exception(exception_address, message="", bcc=None):
    # http://stackoverflow.com/questions/1095601/find-module-name-of-the-originating-exception-in-python
    frm = inspect.trace()[-1]
    mod = inspect.getmodule(frm[0])
    module_name = mod.__name__ if mod else frm[1]

    sender = 'robot@spyne.io'
    recipients = [exception_address]
    if bcc is not None:
        recipients.extend(bcc)

    error_str = ("%s\n\n%s" % (message, traceback.format_exc()))
    msg = MIMEText(error_str.encode('utf8'), 'plain', 'utf8')
    msg['To'] = exception_address
    msg['From'] = 'Spyne <robot@spyne.io>'
    msg['Date'] = formatdate()
    msg['Subject'] = "(%s@%s) %s" % (getpass.getuser(), gethostname(), module_name)

    try:
        smtp_object = smtplib.SMTP('localhost')
        smtp_object.sendmail(sender, recipients, msg.as_string())
        logger.error("Error email sent")

    except Exception as e:
        logger.error("Error: unable to send email")
        logger.exception(e)


def email_text_smtp(addresses, sender=None, subject='', message="",
                                                     host='localhost', port=25):
    if sender is None:
        sender = 'Spyne <robot@spyne.io>'

    exc = traceback.format_exc()
    if exc is not None:
        message = (u"%s\n\n%s" % (message, exc))
    msg = MIMEText(message.encode('utf8'), 'plain', 'utf8')
    msg['To'] = COMMASPACE.join(addresses)
    msg['From'] = sender
    msg['Date'] = formatdate()
    msg['Subject'] = subject

    smtp_object = smtplib.SMTP(host, port)
    if six.PY2:
        smtp_object.sendmail(sender, addresses, msg.as_string())
    else:
        smtp_object.sendmail(sender, addresses, msg.as_bytes())
    logger.info("Text email sent to: %r.", addresses)


def email_text(addresses, sender=None, subject="", message="", bcc=None,
                                                                      att=None):
    if att is None:
        att = {}

    if sender is None:
        sender = 'Spyne <robot@spyne.io>'

    exc = traceback.format_exc()
    if exc is not None and exc != 'None\n' and exc != 'NoneType: None\n':
        message = (u"%s\n\n%s" % (message, exc))
    msg = MIMEText(message.encode('utf8'), 'plain', 'utf8')
    if len(att) > 0:
        newmsg = MIMEMultipart()
        newmsg.attach(msg)
        for k, v in att.items():
            mime_type, encoding = mimetypes.guess_type(k)
            if mime_type == "message/rfc822":
                part = MIMEMessage(message_from_string(v))
            elif mime_type.startswith("image/"):
                part = MIMEImage(v, mime_type.rsplit('/', 1)[-1])
            elif mime_type is not None:
                mime_type_main, mime_type_sub = mime_type.split('/', 1)
                part = MIMENonMultipart(mime_type_main, mime_type_sub)
                part.set_payload(v)
                encode_base64(part)
            else:
                part = MIMEApplication(v)

            newmsg.attach(part)
            part.add_header('Content-Disposition', 'attachment', filename=k)

        msg = newmsg

    msg['To'] = COMMASPACE.join(addresses)
    msg['From'] = sender
    msg['Date'] = formatdate()
    msg['Subject'] = subject

    cmd = ["/usr/sbin/sendmail", "-oi", '--']
    cmd.extend(addresses)
    if bcc is not None:
        cmd.extend(bcc)

    p = Popen(cmd, stdin=PIPE)
    if six.PY2:
        p.communicate(msg.as_string())
    else:
        p.communicate(msg.as_bytes())

    logger.info("Text email sent to: %r.", addresses)
