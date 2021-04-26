from threading import Thread
import socket


class Sender(Thread):
    #método construtor
    def __init__(self, multicast_addr, port, pvt_port, pvt_addr = None):
        Thread.__init__(self)
        self.multicast_addr = multicast_addr
        self.port = port
        self.pvt_port = pvt_port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)
        
    def send(self, data, pvt_addr = None):
        # envia os dados privados
        if (pvt_addr):
            self.s.sendto(data, (pvt_addr, self.pvt_port)) 
        else:
            # envia os dados via multicast
            self.s.sendto(data, (self.multicast_addr, self.port)) 