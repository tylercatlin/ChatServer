# A messaging server that takes multiple special arguments to do things such as message privately
# to run the server, call the file with the arguments [ip address] and [port number]

import argparse
import sys
import socket
import threading
import queue
from time import sleep


s = "Server"
d =''
userlist = list()
socketlist = list()
send_observer = ''
antispam_list = []
kick_socket = 0
kicked = 0
votes = 0
votekicked = 0
votelist = list()

def client_sender(nickname, client_socket: socket.socket,
                  message_queue: queue.Queue,
                  delete_observer_queue_queue):
    messageToSend = '\n>>> ** ' + nickname + ' has entered **' + "\n"
    write(messageToSend, client_socket, message_queue)
    client_socket.send('\n>>> Type /cmds to see the possible commands\n'.encode()) #just tells the user how to use the server
    
    while True:
        message_bytes = client_socket.recv(1024)
        try:
            message = message_bytes.decode().rstrip()
        except UnicodeDecodeError:
            messageToSend = '\n>> ** ' + nickname + ' has quit **' + "\n"
            write(messageToSend, client_socket, message_queue)
            index = userlist.index(nickname)
            userlist.remove(nickname)
            del socketlist[index]
            return
        if len(message) == 0:
            messageToSend = '\n>>> ** ' + nickname + ' has quit **' + "\n"	#If you send a message of length 0, the server kicks you
            write(messageToSend, client_socket, message_queue)
            try:
                index = userlist.index(nickname)
                userlist.remove(nickname)
                del socketlist[index]
            except ValueError:
                p = 1
            kicked = 1
            return
        elif message.startswith('/nick '):
            new_nickname = message.replace('/nick ', '')
            if " " in new_nickname:
                client_socket.send("\n>>> No Spaces Allowed in Your Name!\n".encode())
            else:  																					#Lets users change their nickname. No spaces allowed.
                messageToSend = '\n>>> ** ' + nickname + ' is now known as ' + new_nickname + ' **' + "\n"
                write(messageToSend, client_socket, message_queue)
                              
                index = userlist.index(nickname)
                userlist.remove(nickname)
                nickname = new_nickname
                userlist.insert(index, nickname)
            
            
            
        elif message.startswith('/ulist'):
            ulist =  '\n'.join(userlist)
            messageToSend = "\n>>> User List: \n"
            client_socket.send(messageToSend.encode()) 	#shows the user that sent the command the list of users currently in the server
            client_socket.send(ulist.encode())
            enter = "\n"
            client_socket.send(enter.encode())
            
        
        elif message.startswith('/votekick '):
            kickname = message.replace("/votekick ", '')
            try: 
                userlist.index(kickname)
                messageToSend = "\n>>> " + nickname + " wants to kick " + message[10:] + "!" + "\n"		#initiates a vote to kick a specific person in the server.
                write(messageToSend, client_socket, message_queue)
                initializeVote()
                index2 = userlist.index(message[10:])
                global votekicked
                votekicked = index2           
            except ValueError:
                messageToSend = "\n>>> " + kickname + " was not found." + "\n"	#the person has to actually exist in the server
                write(messageToSend, message_queue, message_queue)
            
        elif message.startswith("/kick "):
            kickname = message.replace("/kick ", '')
            index1 = userlist.index(kickname)
            kick_socket = socketlist[index1]
            del userlist[index1]
            kick_socket.shutdown(socket.SHUT_RDWR)			#hidden command, used to kick people whenever you want
            kick_socket.close()
            if kick_socket == client_socket:
                return
            messageToSend = "\n>>> " + userlist[index1] + " was kicked" + "\n"
            write(messageToSend, client_socket, message_queue)
        
        elif message.startswith('/agree'):
    
                messageToSend = nickname + " agrees!" + "\n"
                write(messageToSend, client_socket, message_queue)
                index = socketlist.index(client_socket)
                votelist[index] = 1							#tied to the votekick option, allows people to vote on if they want the person kicked
                votes = 0
                global votekicked
                for x in votelist:
                    if votelist[x] == 1:
                        votes = votes + 1                        
                if votes>(len(userlist)/2):	#requires 1/2 of the server to agree
                    
                    kick_socket = socketlist[votekicked]
                
                    kick_socket.shutdown(socket.SHUT_RDWR)
                    kick_socket.close()
                    #client_socket.shutdown(socket.SHUT_RDWR)
                    #client_socket.close()
                    messageToSend = "\n>>> " + userlist[votekicked] + " was kicked" + "\n"
                    write(messageToSend, client_socket, message_queue)
                    
                    del userlist[votekicked]
                    kicked = 1
                    if kick_socket == client_socket:
                        return
        
        elif message.startswith('/pm '):
            pmer = message.split(' ', 2)
            if pmer[1] in userlist:
                indexr = userlist.index(pmer[1])
                msg = "\n>>> PM from " + nickname + ": " + pmer[2] + "\n"		#sends personal messages to a specific person. This is why there are
                socketlist[indexr].send(msg.encode())							#no spaces allowed in names.
                print(nickname + " sent '" + pmer[2] + "' to " + pmer[1])
            else:
                msg = "\n>>>User '" + pmer[1] + "' not Found\n"
                client_socket.send(msg.encode())
                
                
        
        elif message.startswith('/cmds'): 
            messageToSend = "Commands:\n"
            messageToSend += "/nick [name] - Use this to rename yourself.\n"
            messageToSend += "/ulist - Use this to see all users in the server.\n"
            messageToSend += "/votekick [name] - Use this to start a vote to kick a user.\n"		#just tells users how to use the server commands
            messageToSend += "/agree - Vote to kick another player.\n"
            messageToSend += "/pm [name] [message] - Send a private message to a user.\n"
            client_socket.send(messageToSend.encode())

        elif not spam_filter(message):
            messageToSend = '\n>>> ' + nickname + ': ' + message + "\n"
            write(messageToSend, client_socket, message_queue)				#sends a message to everyone in the server, as long as it isn't detected as spam
        else:
            print("Spam detected from " + nickname + ": " + message) 
            client_socket.send("\n>>> Message Not Sent: Spam Detected\n".encode())



def write(messageToSend, client_socket: socket.socket, message_queue: queue.Queue):
    print (messageToSend)
    sendMethod(client_socket, messageToSend)								#writes the actual messages to the client
    message_queue.put(messageToSend)
    
def initializeVote():
    for x in socketlist:						#starts up the voting process for kicking, initializes the voter list so we don't have duplicates
        votelist.append(0)


def sendMethod(client_socket: socket.socket, messageToSend):
    try:
        for x in socketlist:
          if x != client_socket:
            x.send(messageToSend.encode()) 			#sends messages to each individual user in the server (socketlist keeps track of their ip/port)
    except OSError:
        p = 1 #trashed OS error exception, if funky look here
            
                 
def kicked (client_socket):
       if kick_socket == client_socket:		#confirms kicking so that the wrong people can't get kicked by threading errors or off-by-one errors
                    return 1
                    

def client_socket_thread(address, client_socket: socket.socket,
                         message_queue: queue.Queue,
                         new_observer_queue_queue: queue.Queue,
                         delete_observer_queue_queue: queue.Queue):
    next_state = ''
    tries = 0
    if kicked == 1:
        kick = 0		#reset kicking status
        return
    else:        
        nickname = address[0] + ':' + str(address[1])		#give them basic nickname of IP+port
        userlist.append(nickname)
        socketlist.append(client_socket)		#add name to both socket list and user list
        observer_queue = queue.Queue()
        new_observer_queue_queue.put((client_socket, observer_queue))
        client_sender(nickname, client_socket, message_queue, delete_observer_queue_queue)
    client_socket.close()

def spam_filter(new_message):

    spam_const = 3   #make this however long you want, longer = less easy to spam the same message

    
    for msg in antispam_list:		#if the message is found is our spam list, it is thrown out and not sent to users
        if msg == new_message:
            antispam_list.append(msg)
            return True
            
    if len(antispam_list) > spam_const:
        antispam_list.remove(antispam_list[0])	#the the list is full, throw out the last entry and add the new one
    
    antispam_list.append(new_message)
    return False			#if no spam was caught, just return false saying that the message is not spam



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("listen_address")
    parser.add_argument("port_number")

    args = parser.parse_args()
    listen_address = args.listen_address
    try:
        port_number = int(args.port_number)		
    except ValueError:
        sys.exit('Port number must be an integer')

    max_port_number = 65535

    if port_number > max_port_number or port_number < 0:
        sys.exit('Port number out of range')

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    #opening a connection using the given arguments
    server_socket.bind((listen_address, port_number))
    server_socket.listen(5)
    print('listening on {0}:{1}'.format(listen_address, port_number))

    message_queue = queue.Queue()		#initialized the message queue for use by users
    new_observer_queue_queue = queue.Queue()		
    delete_observer_queue_queue = queue.Queue()

    try:
        while True:
            client_socket, address = server_socket.accept()
            print('Received a connection from {0}'.format(address))
            
            thread = threading.Thread(target=client_socket_thread,
                                      args=(address, client_socket,			#open up a new thread for a socket to use
                                            message_queue,
                                            new_observer_queue_queue,
                                            delete_observer_queue_queue),
                                      daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print('Main caught keyboard interrupt')

if __name__ == '__main__':
    main()