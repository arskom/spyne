# coding: utf-8

"""Logging utilites."""

import logging
logger = logging.getLogger(__name__)


def log_server_faults(ctx):
    """Event listener for method_fault_object event.

    Logs server faults and ignores client faults.

    """

    fault = ctx.out_error

    if fault.faultcode.startswith('Server'):
        logger.exception(fault)
