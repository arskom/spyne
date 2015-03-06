
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

from socket import gethostname
from email.utils import COMMASPACE, formatdate
from email.mime.text import MIMEText


def email_exception(exception_address, message=""):
    # http://stackoverflow.com/questions/1095601/find-module-name-of-the-originating-exception-in-python
    frm = inspect.trace()[-1]
    mod = inspect.getmodule(frm[0])
    module_name = mod.__name__ if mod else frm[1]

    sender = 'robot@spyne.io'
    receivers = [exception_address]

    error_str = ("%s\n\n%s" % (message, traceback.format_exc()))
    msg = MIMEText(error_str.encode('utf8'), 'plain', 'utf8')
    msg['To'] = exception_address
    msg['From'] = 'Spyne <robot@spyne.io>'
    msg['Date'] = formatdate()
    msg['Subject'] = "(%s@%s) %s" % (getpass.getuser(), gethostname(), module_name)

    try:
        smtp_object = smtplib.SMTP('localhost')
        smtp_object.sendmail(sender, receivers, msg.as_string())
        logger.error("Error email sent")

    except Exception as e:
        logger.error("Error: unable to send email")
        logger.exception(e)


def email_text(addresses, sender=None, subject='', message=""):
    sender = 'robot@spyne.io'
    receivers = addresses

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

    smtp_object = smtplib.SMTP('localhost')
    smtp_object.sendmail(sender, receivers, msg.as_string())
    logger.info("Text email sent to: %r. Text: %s " % (addresses,
                                              message[100:].replace('\n', ' ')))
