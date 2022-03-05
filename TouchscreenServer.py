import asyncio
import sys
import json

class TouchscreenServer:
    def __init__(self, server_name, port, loop):
        self.server_name = server_name
        self.ip_address = "192.168.1.100"
        self.touchscreens = {}
        self.matlab_conn = {}
        self.server = loop.run_until_complete(
            asyncio.start_server(
                self.accept_connection, self.ip_address, port, loop=loop, limit=10000000
                )
            )
        
    @asyncio.coroutine
    def accept_connection(self, reader, writer):
        address_and_port = writer.get_extra_info('peername')
        ip_address = address_and_port[0]
        print("Got a connection from", ip_address)

        if ip_address == self.ip_address and "MATLAB" not in self.matlab_conn:
            print("IP refers to local MATLAB session.\n")
            self.matlab_conn["MATLAB"] = (reader, writer)
            message = ['MATLAB', 'CONNECT']
            token = json.dumps(message)
            writer.write((token + "\n").encode("utf-8"))
            yield from self.handle_matlab(ip_address, reader)

        elif "MATLAB" in self.matlab_conn:
            self.touchscreens[ip_address] = (reader, writer)
            message = [ip_address, 'CONNECT']
            token = json.dumps(message)

            if "MATLAB" in self.matlab_conn:
                print("Alerting MATLAB of new touchscreen connection from", ip_address, "...")
                matlab_writer = self.matlab_conn["MATLAB"][1]
                matlab_writer.write((token + "\n").encode("utf-8"))
            yield from self.handle_touchscreen(ip_address, reader)
            
            if "MATLAB" in self.matlab_conn:
                print(ip_address, "has disconnected from this server.")
                message = [ip_address, 'DISCONNECT']
                token = json.dumps(message)
                matlab_writer = self.matlab_conn["MATLAB"][1]
                matlab_writer.write((token + "\n").encode("utf-8"))
                
        yield from writer.drain()
        
    @asyncio.coroutine
    def handle_touchscreen(self, ip_address, reader):
        while True:
            data = (yield from reader.readline()).decode("utf-8")
            if not data:
                del self.touchscreens[ip_address]
                return None

            message = [ip_address, data.strip()]
            token = json.dumps(message)
            self.send_to_matlab(token)
            
    @asyncio.coroutine
    def handle_matlab(self, ip_address, reader):
        while True:
            data = (yield from reader.readline()).decode("utf-8")
            if not data:
                del self.matlab_conn["MATLAB"]
                return None
                
            self.send_to_touchscreen(json.loads(data.strip()))
            
            
    def send_to_matlab(self, message):
        if "MATLAB" in self.matlab_conn:
            matlab_writer = self.matlab_conn["MATLAB"][1]
            matlab_writer.write((message + "\n").encode("utf-8"))
        
    def send_to_touchscreen(self, list_from_data):
        target_IP = list_from_data[0]
        if target_IP in self.touchscreens:
            target_writer = self.touchscreens[target_IP][1]
            target_writer.write((list_from_data[1] + "\n").encode("utf-8"))
        

if __name__ == "__main__":        
    server_name = "Touchscreen Server"
    port = 50000
    loop = asyncio.get_event_loop()
    server_instance = TouchscreenServer(server_name, port, loop)
    print("Starting", server_name, "on local", server_instance.ip_address, "on port", port, "...")

    try:
        loop.run_forever()
    finally:
        loop.close()
