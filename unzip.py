#!/usr/bin/env python
"""
unzip

Python version of the unzip tool.

Copyright 2016 qimmortal/utonium
"""
# -------------------------------------------------------------------------------- 
# Imports
# -------------------------------------------------------------------------------- 
import argparse
import logging
import os
import Queue
import re
import sys
import threading
import zipfile

# -------------------------------------------------------------------------------- 
# Globals
# -------------------------------------------------------------------------------- 
EXIT_OK = 0
EXIT_ERROR = 1

# -------------------------------------------------------------------------------- 
# Main
# -------------------------------------------------------------------------------- 
def main():
    """ Please run with --help from the command line for the usage message.
    """
    global logger
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logger = logging.getLogger()

    try:
        parser = argparse.ArgumentParser()

        #Usage: unzip [-Z] [-opts[modifiers]] file[.zip] [list] [-x xlist] [-d exdir]
        #  Default action is to extract files in list, except those in xlist, to exdir;
        #  file[.zip] may be a wildcard.  -Z => ZipInfo mode ("unzip -Z" for usage).
        #
        #  -p  extract files to pipe, no messages     -l  list files (short format)
        #  -f  freshen existing files, create none    -t  test compressed archive data
        #  -u  update files, create if necessary      -z  display archive comment
        #  -x  exclude files that follow (in xlist)   -d  extract files into exdir
        #
        #modifiers:                                   -q  quiet mode (-qq => quieter)
        #  -n  never overwrite existing files         -a  auto-convert any text files
        #  -o  overwrite files WITHOUT prompting      -aa treat ALL files as text
        #  -j  junk paths (do not make directories)   -v  be verbose/print version info
        #  -C  match filenames case-insensitively     -L  make (some) names lowercase
        #  -X  restore UID/GID info                   -V  retain VMS version numbers
        #  -K  keep setuid/setgid/tacky permissions   -M  pipe through "more" pager
        #
        #Examples (see unzip.txt for more info):
        #  unzip data1 -x joe   => extract all files except joe from zipfile data1.zip
        #  unzip -p foo | more  => send contents of foo.zip via pipe into program more
        #  unzip -fo foo ReadMe => quietly replace existing ReadMe if archive file newer

        parser.add_argument("-q",
                            dest="quiet", action="store_true", default=None,
                            help="quiet mode")

        parser.add_argument("-o",
                            dest="overwrite", action="store_true", default=None,
                            help="Overwrite exsiting files")
        
        parser.add_argument("-d",
                            type=str, default=None,
                            help="Directory to extract files to")
                            
        parser.add_argument("zipfile",
                            nargs=1, default=None,
                            help="the file to unzip")
        
        parser.add_argument('list', nargs=argparse.REMAINDER)                       

        args = parser.parse_args()

        if args.zipfile is None:
            msg = "Please specify the file to unzip"
            logger.error(msg)
            raise UnzipError(msg)

        the_zipfile = args.zipfile[0]
        if not os.path.exists(the_zipfile):
            msg = "Specified zipfile '%s' does not exist" % the_zipfile
            logger.error(msg)
            raise UnzipError(msg)

        zfh = zipfile.ZipFile(the_zipfile, 'r')

        with BackgroundFileCloser() as bfc:
            for item in zfh.namelist():
                data = zfh.read(item)
                if args.d:
                    item = args.d + '/' + item 
                if '/' in item:
                    subeddir = re.sub('(\/[^\/]+$)', '/', item, count=0)
                    mkdir_recursive(subeddir)

                if item.endswith('/'):            
                    mkdir_recursive(item)
                else:
                    fh = open(item, 'wb')
                    fh.write(data)
                    bfc.close(fh)
                    


    except argparse.ArgumentError, e:
        logger.error("Argument error: %s" % str(e))
        raise

    return EXIT_OK


class BackgroundFileCloser(object):
    """ The Background File Closer pushes file closes into a
        background thread.
    """
    def __init__(self):
        self._running = False
        self._entered = False
        self._threads = []
        self._exc = None

        # Windows defaults to 512 max open file descriptors. Leave a buffer.
        self._queue = Queue.Queue(maxsize=400)
        self._running = True

        for i in range(4):
            t = threading.Thread(target=self._worker, name='backgroundcloser')
            self._threads.append(t)
            t.start()

    def __enter__(self):
        self._entered = True
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._running = False
        for t in self._threads:
            t.join()

    def _worker(self):
        while True:
            try:
                fh = self._queue.get(block=True, timeout=0.100)
                try:
                    fh.close()
                except Exception as e:
                    self._exc = e
            except Queue.Empty:
                if not self._running:
                    break

    def close(self, fh):
        """Schedule a file for closing.
        """
        if not self._entered:
            raise UnzipError("can only call close() when context manager active")

        if self._exc:
            e = self._exc
            self._exc = None
            raise e

        if not self._running:
            fh.close()
            return

        self._queue.put(fh, block=True, timeout=None)


def mkdir_recursive(path):
    # This was working but is handeled in regex for now 
    # Would be good if we can go back and save an import
    #sub_path = os.path.dirname(path)
    #print sub_path + " test subpath"
    #if not os.path.exists(sub_path):
    #   os.makedirs(sub_path)

    if not os.path.exists(path):
       os.makedirs(path)


class UnzipError(Exception):
    pass

# ---------------------------------------------------------------------------------------------
# Execute main and exit with the given status.
# ---------------------------------------------------------------------------------------------
if __name__ == "__main__":
    exit_status = main()
    sys.exit(exit_status)
