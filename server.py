#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys
import signal
import socket
import select, time
import atexit
import ctypes
import psutil

from multiprocessing import Pool, Process, Value, Lock, cpu_count

libc = ctypes.CDLL('libc.so.6')

isblocking = 0
queuedconnections = 128
counter = None

def handleExit():
  libc.prctl(1, 15)
  print("number of thundering herd:%d" % (counter.value()))
  #print 'exit proc'

def WhichCoreIAmOn():
    """if libc is too low to have sched_getcpu"""
    pid=os.getpid()
    fn='/proc/%d/stat' % pid
    with open(fn) as f:
        return int(f.readline().split(' ')[38])



def handleINT(signum,frame):
  """SIGINT handler"""
  #print("signum:%d,frame:%s" % (signum,frame))
  #print("---- good bye pid %d ----" % os.getpid())
  os._exit(0)

class Counter(object):
    """http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing/"""
    def __init__(self, initval=0):
        self.val = Value('i', initval)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.val.value += 1

    def value(self):
        with self.lock:
            return self.val.value

def handle_input(client_socket, data):
    count=0
    sent=0
    sz=len(data)
    try:
        #print("got data:",data)
        while (count<sz):
            sent = client_socket.send(data) # sendall() partial???
            #print("sent out %d bytes\n" % sent)
            count += sent
            if sent == 0:
              raise RuntimeError("socket connection broken")
    except Exception as e:
        """reset by peer error"""
        #print sz, count, sent, socket
        #print "pid=",os.getpid(),",error({0}): {1}".format(e.errno, e.strerror), ", Unexpected error:", sys.exc_info()[0]
        pass

def SpawnIOProcess(ss,v):
    """ss - server socket"""
    #signal.signal(signal.SIGINT,ignoreINT)
    #v.increment()
    #print("global counter: %d" % v.value())
    #time.sleep(2)
    signal.signal(signal.SIGINT,handleINT)
    ep = select.epoll()
    ssno = ss.fileno()
    ep.register(ssno, select.POLLIN|select.EPOLLET) # edge trigger more effective
    #print("register ",ssno," into interest list of pid=",os.getpid())
    connections = {}

    try:
      t1=time.clock()
      while True:
          t2=time.clock()
          if(t2-t1>1):
            t1=t2
            cpuno=WhichCoreIAmOn()
            cpuusage=int(psutil.cpu_percent(0.1,True)[cpuno])
            if(cpuusage > 50):
              time.sleep(0.5)
          #print(cpuusage)
          #a=psutil.cpu_percent(0.1,True)
          events = ep.poll()  # infinitely waiting
          for fileno, event in events:
              if fileno==ssno:
                  try:
                      (client_socket, client_address) = ss.accept() # thundering herd??
                      #print("pid:",os.getpid())
                      lno = client_socket.fileno()
                      #print "got connection from", client_address
                      client_socket.setblocking(isblocking)
                      client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)###????
                      ep.register(lno, select.POLLIN|select.EPOLLET)
                      #print("register ",lno," into interest list of pid=",os.getpid())
                      connections[lno] = client_socket
                  except Exception as e:
                      v.increment()
                      #print "pid=",os.getpid(),",error({0}): {1}".format(e.errno, e.strerror), ", Unexpected error:", sys.exc_info()[0]
                      pass
              else:
                  data=''
                  if event & select.POLLIN:
                      client_socket = connections[fileno]
                      try:
                          data=''
                          tmp=''
                          while True:
                              #print len(data)
                              try:
                                tmp = client_socket.recv(1024)#,select.MSG_DONTWAIT)####??
                                if len(tmp)==0:
                                    break
                                data += tmp
                              except Exception as e:
                                  ##print(len(data), len(tmp))
                                  ##print "pid=",os.getpid(),",error({0}): {1}".format(e.errno, e.strerror), ", Unexpected error:", sys.exc_info()[0]
                                  break
                      except Exception as e:
                          print "pid=",os.getpid(),"|error({0}): {1}".format(e.errno, e.strerror), "|Unexpected error:", sys.exc_info()[0]
                      finally:
                          ##print "len(data)=%d" % len(data)
                          pass
                  if data:
                      #print(len(data))
                      handle_input(client_socket, data)####
                  else:
                      ep.unregister(fileno)####
                      #print("unregister ",fileno," into interest list of pid=",os.getpid())
                      client_socket.close()
                      del connections[fileno]
                      #time.sleep(60)
    except Exception as e:
        print str(e)
    os._exit(0)

if __name__=='__main__':
    try:
      atexit.register(handleExit)
      counter = Counter(0)

      server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      server_socket.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
      server_socket.bind(('192.168.184.133', 2007))
      server_socket.listen(queuedconnections)
      server_socket.setblocking(isblocking)


      #should start multiprocess here!!!
      numOfProc=8
      print("spawn {0} processes, total {1} cores".format(numOfProc, cpu_count()))
      ps=[Process(target=SpawnIOProcess, args=(server_socket,counter)) for i in range(numOfProc)]

      for p in ps: p.start()
      for p in ps: p.join()
    except Exception as e:
      print "pid=",os.getpid(),",error({0}): {1}".format(e.errno, e.strerror), ", Unexpected error:", sys.exc_info()[0]
      pass
    finally:
      sys.exit(0)
