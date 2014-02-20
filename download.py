#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

# Usage: python download.py --feed https://dl.dropboxusercontent.com/u/6160850/downloads.rss --output G:\Python\Test
#python download.py --feed https://dl.dropboxusercontent.com/u/6160850/downloads.rss --output D:\Python\Test
#
#

import sys
import pycurl
from optparse import OptionParser
import feedparser
import os
from datetime import datetime

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass

newDict = {}

def createlog(X,Y):
    fmt = '[%Y-%m-%d %H:%M:%S%Z]'
    event = datetime.now().strftime(fmt)
    if X:
        with open('app.log', 'r') as f:
            for line in f:
                splitLine = line.split(']')
                if int(splitLine[3].replace("[",'').rstrip('\n')) ==1:
                    newDict[splitLine[0][1:]] = ",".join(splitLine[1:-1]).replace("[",'').rstrip('\n')
        filename=Y.split('\\')[-1]
        if filename in newDict.keys():
            i=(newDict[filename].split(',')[-1])
            with open("app.log", "a") as myfile:
                myfile.writelines("[{}][Downloaded]{}[1][{}]\n".format(filename.split('\\')[-1],event,int(i)+1))
        else:
            with open("app.log", "a") as myfile:
                myfile.writelines("[{}][Downloaded]{}[1][1]\n".format(filename.split('\\')[-1],event))
    else:
        print("File Exist")
        with open("app.log", "a") as myfile:
            myfile.writelines("[{}][File Exists]{}[2][0]\n".format(Y.split('\\')[-1],event))

# Get args
def main():
    parser = OptionParser(usage="%prog [options] <url>")
    parser.add_option("-u","--feed", default=False, dest="url", help="RSS Feed URL", metavar="URL")
    parser.add_option( "-p", "--output", default=False, dest="path", help="Download File PATH", metavar="PATH")
    opts, args = parser.parse_args()
    URL=opts.url
    print(URL)
    print(opts)
    print(args)

    #Parsing the RSS Feed
    feed=feedparser.parse(URL)
    title = feed['entries'][1].title
    description =  feed['entries'][1].summary,
    url = feed['entries'][1].link,
    posts = []
    for i in range(0,len(feed['entries'])):
        posts.append({
            'title': feed['entries'][i].title,
            'description': feed['entries'][i].summary,
            'url': feed['entries'][i].link,
        })
        print("{}. {}".format(i+1,posts[i]['title']))

    FileNo = input('Please enter File Index NO.: ')
    index = map(int, set(FileNo.split(',')))
    #print(sys.getsizeof(index))

    # Make a queue with (url, filename) tuples
    queue = []
    num_conn = 10
    i=0
    for url in index:
        print(url)
        filename = opts.path+'\\'+posts[url-1]['url'].split('/')[-1]
        queue.append((posts[url-1]['url'], filename))
        i=i+1
    print(i)
    num_conn=i

    # Check args
    assert queue, "no URLs given"
    num_urls = len(queue)
    num_conn = min(num_conn, num_urls)
    assert 1 <= num_conn <= 10000, "invalid number of concurrent connections"
    print("PycURL %s (compiled against 0x%x)" % (pycurl.version, pycurl.COMPILE_LIBCURL_VERSION_NUM))
    print("----- Getting", num_urls, "URLs using", num_conn, "connections -----")

    m = pycurl.CurlMulti()
    m.handles = []

    if os.path.exists(filename):
            createlog(False,filename)
    else:
        # Pre-allocate a list of curl objects
        print("Downloading ... ... [Please Wait]")
        for i in range(num_conn):
            c = pycurl.Curl()
            c.fp = None
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.MAXREDIRS, 5)
            c.setopt(pycurl.CONNECTTIMEOUT, 30)
            c.setopt(pycurl.TIMEOUT, 300)
            c.setopt(pycurl.NOSIGNAL, 1)
            m.handles.append(c)

        # Main loop
        freelist = m.handles[:]
        num_processed = 0
        while num_processed < num_urls:
            # If there is an url to process and a free curl object, add to multi stack
            while queue and freelist:
                url, filename = queue.pop(0)
                c = freelist.pop()
                #print(os.path.getsize(filename))
                c.setopt(pycurl.URL, url)
                if os.path.exists(filename):
                    c.fp = open(filename, "ab")
                    c.setopt(pycurl.RESUME_FROM,os.path.getsize(filename))
                else:
                    c.fp = open(filename, "wb")
                c.setopt(pycurl.WRITEDATA, c.fp)
                m.add_handle(c)
                # store some info
                c.filename = filename
                c.url = url
            # Run the internal curl state machine for the multi stack
            while 1:
                ret, num_handles = m.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break
            # Check for curl objects which have terminated, and add them to the freelist

            while 1:
                num_q, ok_list, err_list = m.info_read()
                for c in ok_list:
                    c.fp.close()
                    c.fp = None
                    m.remove_handle(c)
                    print("Success:", c.filename)
                    createlog(True,c.filename)
                    freelist.append(c)
                for c, errno, errmsg in err_list:
                    c.fp.close()
                    c.fp = None
                    m.remove_handle(c)
                    print("Failed: ", c.filename, c.url, errno, errmsg)
                    freelist.append(c)
                num_processed = num_processed + len(ok_list) + len(err_list)
                if num_q == 0:
                    break
            # Currently no more I/O is pending, could do something in the meantime
            # (display a progress bar, etc.).
            # We just call select() to sleep until some more data is available.
            m.select(1.0)

    # Cleanup
    for c in m.handles:
        if c.fp is not None:
            c.fp.close()
            c.fp = None
        c.close()
    m.close()

if __name__ == '__main__':
    main()
