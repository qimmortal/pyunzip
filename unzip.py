import Queue
import threading
import os
import zipfile
import re

my_archive = "firefox-47.0a1.en-US.win32.reftest.tests.zip"

archive = zipfile.ZipFile(my_archive, 'r')

class BackgroundFileCloser(object):
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
        """Schedule a file for closing."""
        if not self._entered:
            raise Exception('can only call close() when context manager active')

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
       #print "test 1 " + sub_path
    if not os.path.exists(path):
       os.makedirs(path)
       #print "test 2 " + path
        
        

        
with BackgroundFileCloser() as bfc:
    for item in archive.namelist():
        data = archive.read(item)
        if '/' in item:
            subeddir = re.sub('(\/[^\/]+$)', '/', item, count=0)
            mkdir_recursive(subeddir)
        if item.endswith('/'):            
            mkdir_recursive(item)
        else:
            #print item, len(data)
            fh = open(item, 'wb')
            fh.write(data)
            bfc.close(fh)