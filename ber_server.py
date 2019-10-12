'''# socket design and testing file for bit error rate 
   # with channel emulator
   __AUTHOR__="Subharthi Banerjee"
   @Done: throughput calculation  ()
	

	@TODO: ctrl+c does not close the thread
	it waits to recv from socket. Solve this issue
	to close thread in the Ubuntu

	@TODO: check why a lot of packets not working
	for UDP. Even in local host.

	*** check if linux then bind to oai0
	if not do not bind

	*** check non-blocking for thread execution

	** add more data to the message by a multiplier


	# add exit table. The code should integrate the user
	keyboardinterrupt and a detailed report of execution

'''

import socket
import os
import sys
import logging
import argparse
import signal 
from functools import partial
import threading
import time
import Colorer
timestr = time.strftime("%Y%m%d-%H%M%S")
log_filename="lte_udp_test_log_"+timestr+'.txt'
log_raw = "lte_udp_received_bytes_"+timestr+'.txt'

from prettytable import PrettyTable
# UDP addressed from nasmesh
UDP_ENB_ADDR = 'localhost'#"10.0.1.1"
UDP_UE_ADDR = "10.0.1.2"

# server if 0
server_or_client = 0
n_packets = 100

UDP_PORT = 5005

table_header = ['Throughput (Mbps)', 'BER(%)', 'Total Bytes', 'Number of Packets']
message = [0xAA, 0x55, 0xA5, 0X5A, 0xA1, 0xA4, 0xA9, 0xAF, 0x5A, 0x7A, 0x11]
fake_data = [0xAD, 0x55, 0xA5, 0X5A, 0xA1, 0xA4, 0xA9, 0xAF, 0x5A, 0x7A, 0x11]


logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


lock = threading.Lock()
# ======================== ARGUMENT PARSING =================================

def parse_arguments():

	"""
	@TODO: add n_packets as variable
	"""
	
	global server_or_client
	global n_packets
	parser = argparse.ArgumentParser()

	parser.add_argument("--server_or_client","-soc", help="Set 0 or 1 for server or client")
	parser.add_argument("--n_packets","-np", help="Number of packets")
	parser.add_argument("-V", "--version", help="show program version", action="store_true")


	args = parser.parse_args()
	if args.server_or_client:
		server_or_client = int(args.server_or_client)
		if server_or_client == 0:
			logging.info("Running for server")
		elif server_or_client == 1:
			logging.info("Running client")
		else:
			print("Invalid option for [--server_or_client] %s", args.server_or_client)


	if args.n_packets:
		n_packets = int(args.n_packets)
		
		logging.info("Running for %d packets", n_packets)
		
	else:
		print("Invalid option for [--n_packets] %s, Running for default value", args.n_packets)
# ===========================================================================


def ber_byte(received_byte, transmitted_byte):
	"""
		args: 
			received_byte: received byte in order
			transmitted_byte: transmitted byte in order
		rtype: 
			ber: number of bits that are erroneaous
			for example: received_byte = 	10001100
						 transmitted_byte=	10000010
						 ---------------------------
						 					00001110
			number of bits in error					 					
	"""
	# xor of two bytes to find number of mismatches
	error = received_byte ^ transmitted_byte   		
	# bit error rate = error/number_of_bits	
	ber = count_ones(error)		# 

	return ber

def time_it(method):
	"""
	"""
	def times(*args, **kwargs):
		ts = time.time()
		result = method(*args, **kwargs)
		te = time.time()
		return result
	
	return times

def throughput(total_bytes, time):
	"""
	"""

	return ((total_bytes*8)//time)*1e-3


def count_ones(byte):
	"""
		rtype: number of set bits

	"""
	binary = bin(byte)
	return len([ones for ones in binary[2:] if ones=='1'])


class ThreadedServer(threading.Thread):
	"""
	"""
	def __init__(self, host, port, sock):
		self.host = host
		self.port = port
		self.sock = sock
		self.sock.bind((self.host, self.port))
		self.kill_received = False
		self.outfile = None
		self.outfile_raw = None
		self.throughput = [] # list to calculate average and max
		self.delay = []
		self.ber = []

		threading.Thread.__init__(self)
		
		
	
		
	def run(self):
		"""
			thread running and receiving from server
		"""
		ber = 0
		global message
		recv_n_packets = 0
		logging.info('Running thread...')
		tp = 0
		T = 0
		Tp = 0
		print("|-----------------------------------|")
		self.outfile = open(log_filename, 'w+')
		self.outfile_raw = open(log_raw, 'w+')
		

		try:
			while not self.kill_received:
				#logging.info(self.sock)
				ts = time.time()
				data, address = self.sock.recvfrom(len(message)+4)
				te = time.time()

				T += (te-ts)
				
				recv_n_packets += 1
				string = "|Received {0:5d} bytes from client at {1:5f} s|\n".format(len(data), T)
				#print(string)
				logging.debug("Writing to file %s", string)
				self.outfile.write(string)
				logging.debug("Returned from %s", address)
				#print("|---------------------------------------------|")
				#print([hex(x) for x in data])
				
				if data:
					tp += len(data)
					
					if len(data) == len(message) + 1:
						for msg, dat in zip(message,data[1:]):
							ber += ber_byte(msg, dat)
					elif len(data) == len(message) + 2:
						for msg, dat in zip(message,data[2:]):
							ber += ber_byte(msg, dat)
					else:
						logging.info("Something went wrong or out of sequence")

					data = [hex(x) for x in data] 
					#print(data)
					self.outfile_raw.writelines("%s  " % dt for dt in data)
					self.outfile_raw.write("\n")
					

					if recv_n_packets % (n_packets//5) == 0:
							logging.info("Succesfully received %d packets", recv_n_packets)


					if recv_n_packets == n_packets:
						ber = ber/(len(data)*recv_n_packets*8)
						ber = ber * 100
						Tp = throughput(tp, T)
						self.throughput.append(Tp)
						self.ber.append(ber)
						self.delay.append(T)
						## little bit verbose to check operation

						

						print("\n\n\n")
						logging.info("Received %d packets", recv_n_packets)
						print('Results -----------------')
						t = PrettyTable(table_header)
						t.add_row([Tp, ber, tp, n_packets])
						print("\n\n\n\n")
						print(t)
						logging.info("writing to file ...")
						self.outfile.write(t.get_string())
						self.outfile.write("\n")
						ber = 0
						
						recv_n_packets = 0

						#lock.release()
						Tp = 0
						tp = 0
						T = 0
						

						print("|---------------------------------------------|")
						print("|---------------------------------------------|")
						print("\n\n\n\n\n")
						print("|---------------------------------------------|")
						print("|---------------------------------------------|")
		except (KeyboardInterrupt, SystemExit, IOError) as e:
			
			logging.error("Exiting.. %s", e)
			#self.outfile.close()  # close if file is not closed
			self.close()
			
			self.outfile_raw.close()


	def close(self):
		"""
			cleaning up threads and sockets
		"""
		logging.info("closing/stopping sockets and threads")
		self.sock.close()
		try:
			self.join()
		except RuntimeError:
			logging.error("Something went wrong with joining thread")

		sys.exit(0)
		




def server_start(sock, ip_addr, port):
	"""
		rtype: socket object after bind
	"""
	print("*********************************************")
	print("---------- Starting UDP Server -------------")
    
	print("--------------------------------------------")
	addr= (ip_addr, port)
	print("Starting up server on ip" , addr)

	sock.bind(addr)
	return sock




def terminate_process(sock, signal_number, frame):
	try:
		print("Trying to terminate_process")
		sock.close()
		sys.exit(0)
	
	except OSError:
		print("Some exception happened")
		sys.exit(0)
	
		
def has_livethreads(threads):
	return True in [t.isAlive() for t in threads]



def client_send(sock, ip_addr, port):
	"""
		client should check non-blocking mode
		clinet should also check if it has send all 
		the packets. Check if overflow occurred.
		Please do a client summary for better check.

		This happens in both localhost and oai0.
		Needs to check priority(1)

	"""

	global message
	print("*********************************************")
	print("---------- Starting UDP Client -------------")
    
	print("--------------------------------------------")
	addr = (ip_addr, port)
	
	print("Starting up client ", addr)
	send_n_packets = 0
	for i in range(0, n_packets):

		try:
			send_n_packets+=1

			msg = message.copy()
			if i <= 255:
				msg.insert(0, i)
			# remove headers for IP and UDP
			elif i>255 and i<65507: 
				ilow = i & 0x00FF    # lower byte
				logging.debug("before adding high low byte %d", len(msg))
				msg.insert(0, ilow)
				ihigh=i>>8			 # higher byte
				msg.insert(0, ihigh)
				logging.debug("here adding high low byte %d", len(msg))
				
			msg = bytearray(x for x in msg)
			logging.debug("message size is now:  %d", len(msg))
			assert sock.sendto(msg, addr) == len(msg)
			logging.debug("last packet sent %d", send_n_packets)

		except IOError as e:
			print("Error code: ", e)
			sock.close()
		finally:
			# check how many packets are sent
			if send_n_packets == n_packets:
				logging.info("------------- Sent %d packets------------", send_n_packets)
				send_n_packets = 0
				time.sleep(1)  # sleep for 1s
	sock.close()


def main():

	
	parse_arguments()
	threads = []
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	#sock.setblocking(0)
	#sock.settimeout(2.0)
	# for server
	if server_or_client == 0:
		threads = []
		print("Server starting..")
		#sock = server_start(sock, 'localhost', UDP_PORT)
		udpserver = ThreadedServer(UDP_ENB_ADDR, UDP_PORT, sock)
		signal.signal(signal.SIGINT, partial(terminate_process, sock))
		print('Receiving from client -- threaded')
		threads.append(udpserver)
		udpserver.start()
		while has_livethreads(threads):
			try:
				[t.join(1) for t in threads
				 if t is not None and t.isAlive()]
			except (KeyboardInterrupt, SystemExit, IOError):
				logging.info("Killing all threads..")
				for t in threads:
					t.kill_received = True
					
					
					logging.info("House keeping with final results for %d runs", len(udpserver.throughput))
					final_header = ["Max Throughput", "Avg Throughput", "Min Delay", "Avg Delay", "Min BER", "Avg BER"]
					tab = PrettyTable(final_header)
					tab.add_row([max(udpserver.throughput), sum(udpserver.throughput)//len(udpserver.throughput),
						       min(udpserver.delay), sum(udpserver.delay)/len(udpserver.delay),
						       min(udpserver.ber), sum(udpserver.ber)//len(udpserver.ber)])
					print(tab)
					print()
					t.outfile.write(tab.get_string())
					t.outfile.close()
					t.outfile_raw.close()
					logging.info("Closed outfiles..")


			
		#sock.close()
		print("bye..")

	elif server_or_client == 1:
		
		print("Client starting..")
		
		client_send(sock, UDP_ENB_ADDR, UDP_PORT)
		
		
	else:
		print("Invalid option")
	
	



if __name__=="__main__":
	main()