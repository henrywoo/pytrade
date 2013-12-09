#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from socket import *              # portable socket interface plus constants
import datetime
import os
import time

def sendall2(sock, data):
  while data:
    sent = sock.send(data)
    data = data[sent:]
#sockobj = socket(AF_INET, SOCK_STREAM)      # make a TCP/IP socket object
#sockobj.connect((serverHost, serverPort))   # connect to server machine + port

def run(sz,cnum):
  serverHost = '192.168.184.133'          # server name, or: 'starship.python.net'
  serverPort = 2007                # non-reserved port used by the server
  message = [b'H'*sz]*cnum          # default text to send to server # requires bytes: b'' or str,encode()
  t1 = datetime.datetime.now()
  counter=0
  for line in message:
    counter+=1
    try:
      sockobj = socket(AF_INET, SOCK_STREAM)      # make a TCP/IP socket object
      sockobj.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      sockobj.setsockopt(SOL_SOCKET, TCP_NODELAY, 1)
      if counter%3==1:
        sockobj.bind(('192.168.184.131', 0))
      elif counter%3==2:
        sockobj.bind(('192.168.184.135', 0))
      else:
        sockobj.bind(('192.168.184.136', 0))
      sockobj.connect((serverHost, serverPort))   # connect to server machine + port
      sockobj.setblocking(0)
      #sockobj.send(line)                      # send line to server over socket
      sendall2(sockobj,line)                      # send line to server over socket
      leng=0
      data=''
      #print(len(line))
      while leng<len(line):
          try:
              tmp = sockobj.recv(1024)               # receive line from server: up to 1k
          except Exception as ex:
              #print "pid=",os.getpid(),"|error({0}): {1}".format(e.errno, e.strerror), "|Unexpected error:", sys.exc_info()[0]
              continue
          leng += len(tmp)
          data += tmp
      if len(data)!=sz:
          print "packet dropped!!"
      #print(len(data))
      ##print('Client received:', data)         # bytes are quoted, was `x`, repr(x)
      sockobj.close()                             # close socket to send eof to server
    except Exception as e:
      print "pid=",os.getpid(), "|error:", str(e), "|Unexpected error:", sys.exc_info()[0]
      print counter, cnum
      sys.exit(0)
      pass
  t2 = datetime.datetime.now()
  c=(t2-t1)
  print("payload={0},number={1},time={2}s{3}us".format(sz,counter,c.seconds,c.microseconds))
  print("sleep for %d seconds" % 5)
  time.sleep(5)

if len(sys.argv)<2:
  print "argument too few"
  sys.exit(0)
ln=int(sys.argv[1])

cnum=10000
[run(10240,cnum*(1+i)) for i in range(ln)]
