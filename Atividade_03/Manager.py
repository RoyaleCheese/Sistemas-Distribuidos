import sys
from threading import Thread
sys.path.append(".")
from Client import Client
from Message import Message
from Sender import Sender
from Receiver import Receiver
from Receiver_pvt import Receiver_pvt
from Listener import Listener
import os

"""
    Chat Multicast e privado
    Desenvolvedores: Brendow e Lucas

    Classe:     Manager

    Execução:   python3 Manager.py

    Funcionamento:  Realiza o gerenciamento (conexão, adição e remoção) dos clientes e mensagens
                    Definindo quais funções devem ser aplicadas à mensagem recebida ou à ser enviada
"""

#Classe principal que gerencia os clientes e mensagens
class Manager:
    #método construtor
    def __init__(self):
        #lista de conectados
        self.connected = []

        #lista de nomes conectados
        self.names_connected = []

        #instancia um cliente
        self.client = Client()
        
        #threads
        #envio
        self.ts = None
        #recebimento multicast
        self.tr = None
        #recebimento privado
        self.trp = None
        #listener para entrada do teclado
        self.tl = None

        #flag de controle para que não seja enviado mais que uma mensagem (type 3)
        self.is_first_message = True

    #função que inicializa a threads
    def set_threads(self, manager):
        self.ts = Sender(self.client.multicast_addr, self.client.port, self.client.pvt_port)
        self.ts.start()
        self.tr = Receiver(self.client.multicast_addr, self.client.port, manager)
        self.tr.start()
        self.trp = Receiver_pvt(manager)
        self.trp.start()
        self.tl = Listener(manager)
        self.tl.start()

    #fecha a conexão com os sockets
    def stop_threads(self):
        self.ts.close()
        self.tr.close()
        self.trp.close()

    #adiciona um usuário na lista de conectados
    def add_user(self, client):
        self.connected.append(client)
        self.names_connected.append(client.nick)

    #remove um usuário da lista de conectados
    def pop_user(self, client):
        if (client in self.connected):
            self.connected.remove(client)
        self.names_connected.remove(client.nick)
        print("------------------------------")
        print(client.nick, "saiu do chat")
        print("------------------------------")

    #imprime a lista de conectados
    def show_connected(self):
        print("------------------------------")
        print("Lista de Conectados:")
        for person in self.connected:
            print(person.nick)
        print("------------------------------")


    #Filtra a mensagem de entrada em usuário e mensagem a ser enviada
    def filter_msg(self, data, ch = " "):
        cli = None
        index = [i for i, ltr in enumerate(data) if ltr == ch]
        name = data[index[0]+1: index[1]]
        for person in self.connected:
            if person.nick == name:
                cli = person 
        msg = data[index[1]+1:]
        return cli, msg

    #define um objeto de mensagem para fazer o envio
    def set_msg(self, data):
        msg = None
        if (len(data) == 1):
            if "TO" in data[0]:
                dst_cli, text = self.filter_msg(data[0])
                msg = Message(4, self.client, len(text), text, dst_cli.pvt_addr)
                if (dst_cli == self.client):
                    print(msg.message)
            elif "COMMANDS" in data[0]:
                self.show_commands()
            elif "SHOW_ALL" in data[0]:
                self.show_connected()
            elif "LEAVE" in data[0]:
                msg = Message(5, self.client, len(""), "")
            else:
                text = data[0]
                msg = Message(3, self.client, len(text), text)
        else:
            msg = Message(data[0], data[1], data[2], data[3])
        return msg

    #imprime mensagem privada
    def print_pvt(self, msg):
        print("------------------------------")
        print ("Mensagem privada de " + msg.source.nick + ": " + msg.message)
        print("------------------------------")

    #gerencia a mensagem
    def manage_msg(self, msg):

        #verifica se a mensagem é do tipo join
        if (msg.type == 1):

            #caso o join recebido seja do cliente
            if (msg.source.nick == self.client.nick):
                
                #se o cliente não está na lista de conectados
                if (self.client.nick not in self.names_connected):
                    #cria o pacote a partir da mensagem
                    pckg = msg.get_package()

                    #dá o join no cliente
                    self.join(pckg)

            #caso o join recebido não seja do cliente
            else:
                #adiciona a fonte da mensagem na lista de conectados
                self.add_user(msg.source)
                print("------------------------------")
                print(msg.source.nick, "entrou no chat.")
                print("------------------------------")
                #envia um join_ack
                self.join_ack()

        #se o join_ack não for do cliente
        elif(msg.type == 2 and msg.source.nick != self.client.nick):
            
            #se a fonte do join_ack não está na lista de conectados
            if (msg.source.nick not in self.names_connected):
                self.add_user(msg.source)

        #se a mensagem nao foi enviada por esse cliente
        elif(msg.type == 3 and msg.source.nick != self.client.nick):
            self.receive_message(msg)
            
        #se a mensagem foi enviada por esse cliente
        elif(msg.type == 3 and msg.source.nick == self.client.nick):
            if (self.is_first_message):
                self.is_first_message = False
                pckg = msg.get_package()
                self.ts.send(pckg)
            else:
                self.is_first_message = True

        #caso a mensagem for privada mas é de outra fonte
        elif (msg.type == 4 and msg.source.nick != self.client.nick):
            self.print_pvt(msg)

        #caso a mensagem seja privada e seja do mesmo cliente
        elif (msg.type == 4 and msg.source.nick == self.client.nick):
            pckg = msg.get_package()
            self.ts.send_pvt(pckg, msg.dest)

        #remove o cliente que saiu da lista
        elif (msg.type == 5 and msg.source.nick != self.client.nick):
            self.pop_user(msg.source)

        #finaliza a conexão do cliente
        elif (msg.type == 5 and msg.source.nick == self.client.nick):
            pckg = msg.get_package()
            self.ts.send(pckg)
            self.ts.stop = True
            print("------------------------------")
            print("Conexão encerrada.")
            print("------------------------------")
            self.stop_threads()
            os._exit(0)

    #imprime os comandos do chat na tela
    def show_commands(self):
        print("------------------------------")
        print("Lista de comandos:")
        print("TO nomedousuario mensagem : Comando para enviar mensagens privadas.")
        print("SHOW_ALL : Mostra o nome de todos usuários conectados.")
        print("LEAVE : Sai do chat")
        print("------------------------------")

    #realiza o join
    def join(self, pckg):
        #envia o pacote para todos os clientes
        self.ts.send(pckg)
        #adiciona o cliente na lista de conectados
        self.add_user(self.client)
        print ("Olá " + self.client.nick + " você foi conectado")
        print("Digite COMMANDS para ver os comandos")
        print("------------------------------")

    #realiza o join_ack
    def join_ack(self):
        #cria a mensagem a partir de uma lista
        msg = self.set_msg([2, self.client, 0, ""])
        
        #recebe o valor da mensagem em um pacote de bytes
        pckg = msg.get_package()

        #envia o pacote
        self.ts.send(pckg)

    def receive_message(self, msg):
        print(msg.source.nick + " disse a todos: " + msg.message)

    #conecta o cliente
    def connect(self):
        #cria a mensagem a partir de uma lista
        msg = self.set_msg([1, self.client, 0, ""])
        
        #define o que fazer com a mensagem
        self.manage_msg(msg)


#objeto do gerenciador
manager = Manager()

#inicializa a threads
manager.set_threads(manager)

#conecta o cliente
manager.connect()