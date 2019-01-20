# encoding: utf8
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

#
# Copyright (c) 2004-2016, CherryPy Team (team@cherrypy.org)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the CherryPy Team nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

import logging
logger = logging.getLogger(__name__)

import os, re, sys

from spyne.util.color import YEL

# _module__file__base is used by Autoreload to make
# absolute any filenames retrieved from sys.modules which are not
# already absolute paths.  This is to work around Python's quirk
# of importing the startup script and using a relative filename
# for it in sys.modules.
#
# Autoreload examines sys.modules afresh every time it runs. If an application
# changes the current directory by executing os.chdir(), then the next time
# Autoreload runs, it will not be able to find any filenames which are
# not absolute paths, because the current directory is not the same as when the
# module was first imported.  Autoreload will then wrongly conclude the file
# has "changed", and initiate the shutdown/re-exec sequence.
# See cherrypy ticket #917.
# For this workaround to have a decent probability of success, this module
# needs to be imported as early as possible, before the app has much chance
# to change the working directory.
_module__file__base = os.getcwd()

try:
    import fcntl
except ImportError:
    MAX_FILES = 0
else:
    try:
        MAX_FILES = os.sysconf('SC_OPEN_MAX')
    except AttributeError:
        MAX_FILES = 1024



class AutoReloader(object):
    """Monitor which re-executes the process when files change.

    This :ref:`plugin<plugins>` restarts the process (via :func:`os.execv`)
    if any of the files it monitors change (or is deleted). By default, the
    autoreloader monitors all imported modules; you can add to the
    set by adding to ``autoreload.files``::

        spyne.util.autorel.AutoReloader.FILES.add(myFile)


        spyne.util.autorel.AutoReloader.match = r'^(?!cherrypy).+'

    The autoreload plugin takes a ``frequency`` argument. The default is
    1 second; that is, the autoreloader will examine files once each second.
    """

    FILES = set()
    """The set of files to poll for modifications."""

    def __init__(self, frequency=1, match='.*'):
        self.max_cloexec_files = MAX_FILES

        self.mtimes = {}
        self.files = set(AutoReloader.FILES)

        self.match = match
        """A regular expression by which to match filenames.

        If there are imported files you do *not* wish to monitor, you can
        adjust the ``match`` attribute, a regular expression. For example,
        to stop monitoring cherrypy itself, try ``match=r'^(?!cherrypy).+'``\\.
        """

        self.frequency = frequency
        """The interval in seconds at which to poll for modified files."""

    def start(self):
        from twisted.internet.task import LoopingCall

        retval = LoopingCall(self.run)
        retval.start(self.frequency)
        return retval # oh no

    def sysfiles(self):
        """Return a Set of sys.modules filenames to monitor."""
        files = set()
        for k, m in list(sys.modules.items()):
            if re.match(self.match, k):
                if (
                    hasattr(m, '__loader__') and
                    hasattr(m.__loader__, 'archive')
                ):
                    f = m.__loader__.archive
                else:
                    try:
                        f = getattr(m, '__file__', None)
                    except ImportError:
                        f = None

                    if f is not None and not os.path.isabs(f):
                        # ensure absolute paths so a os.chdir() in the app
                        # doesn't break me
                        f = os.path.normpath(
                            os.path.join(_module__file__base, f))
                files.add(f)
        return files

    def run(self):
        """Reload the process if registered files have been modified."""
        for filename in self.sysfiles() | self.files:
            if filename:
                if filename.endswith('.pyc'):
                    filename = filename[:-1]

                oldtime = self.mtimes.get(filename, 0)
                if oldtime is None:
                    # Module with no .py file. Skip it.
                    continue

                try:
                    mtime = os.stat(filename).st_mtime
                except OSError:
                    # Either a module with no .py file, or it's been deleted.
                    mtime = None

                if filename not in self.mtimes:
                    # If a module has no .py file, this will be None.
                    self.mtimes[filename] = mtime
                else:
                    if mtime is None or mtime > oldtime:
                        # The file has been deleted or modified.
                        logger.info("Restarting because '%s' has changed." %
                                                                       filename)

                        from twisted.internet import reactor
                        reactor.stop()
                        self._do_execv()
                        return

    @staticmethod
    def _extend_pythonpath(env):
        """
        If sys.path[0] is an empty string, the interpreter was likely
        invoked with -m and the effective path is about to change on
        re-exec.  Add the current directory to $PYTHONPATH to ensure
        that the new process sees the same path.

        This issue cannot be addressed in the general case because
        Python cannot reliably reconstruct the
        original command line (http://bugs.python.org/issue14208).

        (This idea filched from tornado.autoreload)
        """

        path_prefix = '.' + os.pathsep
        existing_path = env.get('PYTHONPATH', '')
        needs_patch = (
            sys.path[0] == '' and
            not existing_path.startswith(path_prefix)
        )

        if needs_patch:
            env["PYTHONPATH"] = path_prefix + existing_path

    def _set_cloexec(self):
        """Set the CLOEXEC flag on all open files (except stdin/out/err).

        If self.max_cloexec_files is an integer (the default), then on
        platforms which support it, it represents the max open files setting
        for the operating system. This function will be called just before
        the process is restarted via os.execv() to prevent open files
        from persisting into the new process.

        Set self.max_cloexec_files to 0 to disable this behavior.
        """
        for fd in range(3, self.max_cloexec_files):  # skip stdin/out/err
            try:
                flags = fcntl.fcntl(fd, fcntl.F_GETFD)
            except IOError:
                continue
            fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

    def _do_execv(self):
        """Re-execute the current process.

        This must be called from the main thread, because certain platforms
        (OS X) don't allow execv to be called in a child thread very well.
        """
        args = sys.argv[:]

        self._extend_pythonpath(os.environ)

        logger.info('Re-spawning %s' % ' '.join(args))
        logger.info("")
        logger.info("%s Bye! %s", YEL("-" * 35), YEL("-" * 35))
        logger.info("")

        if sys.platform[:4] == 'java':
            from _systemrestart import SystemRestart
            raise SystemRestart

        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]

        os.chdir(_module__file__base)
        logger.debug("Change working directory to: %s", _module__file__base)

        if self.max_cloexec_files:
            self._set_cloexec()

        os.execv(sys.executable, args)
