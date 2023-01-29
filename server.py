#!/bin/env python3

from time import time
import asyncio, socket
import ssl

from modbus_exception import modbus_exception
from modbus_functions import func_dict

MODBUS_TCP_MAX_BUF_LEN = 253 + 7

class modbus_request:
    def __init__(self, buf):
        self.parse_request(buf)

    def parse_request(self, buf):
        self.tran_id = int.from_bytes(buf[0:2], byteorder='big')
        self.proto_id = int.from_bytes(buf[2:4], byteorder='big')
        self.len_field = int.from_bytes(buf[4:6], byteorder='big')
        self.unit = int.from_bytes(buf[6:7], byteorder='big')
        self.fcode = int.from_bytes(buf[7:8], byteorder='big')
        self.data = buf[8:]

class modbus_response:
    def __init__(self, req, fcode, data):
        self.build_response(req, fcode, data)

    def build_response(self, req, fcode, data):
        self.tran_id = req.tran_id
        self.proto_id = req.proto_id
        self.len_field = 2 + len(data)
        self.unit = req.unit
        self.fcode = fcode
        self.data = data

def check_fcode(fcode):
    try:
        func_dict[fcode]
        res = True
    except KeyError:
        res = False

    return res

def check_pdu(fcode, data):
    if not check_fcode(fcode):
        return modbus_exception.ILLEGAL_FUNCTION

    if len(data) < 2:
        return modbus_exception.ILLEGAL_DATA_ADDRESS

    if 0x0 < fcode and fcode <= 0x6 and len(data) == 4:
        return None
    elif fcode == 0xF and len(data) > 6:
        return None
    elif fcode == 0x10 and len(data) > 7:
        return None

    return modbus_exception.ILLEGAL_DATA_VALUE

def have_modbus_exception(req, fcode, error):
    res_fcode = fcode + 0x80
    res_data = error.to_bytes(length=1, byteorder='big')
    return res_fcode, res_data

class modbus_client:
    def __init__(self, reader, writer, max_elapsed_time=2):
        self.reader = reader
        self.writer = writer
        self.max_elapsed_time = max_elapsed_time
        self.timing_started = False

    def start_timing(self):
        self.begin = time()
        self.timing_started = True

    def stop_timing(self):
        self.timing_started = False

    def is_timeout(self):
        return self.timing_started and (time() - self.begin > self.max_elapsed_time)

    def close(self):
        self.writer.close()

class modbus_server:
    def __init__(self, host='127.0.0.1', port=5020, unit=1):
        self.host = host
        self.port = port
        self.unit = unit

    def _is_this_unit(self, unit):
        if unit == 0 or unit == self.unit:
            return True
        else:
            return False

    def _frame_ready(self, buf):
        if len(buf) < 8:
            return False
        return True

    def _check_header(self, req):
        if req.proto_id != 0 or \
           req.len_field != 1 + 1 + len(req.data) or \
           not self._is_this_unit(req.unit):
            return False
        return True

    def _have_modbus_request(self, buf):
        return modbus_request(buf)

    def _print_client(self, client, req):
        client_info = "Client {} ".format(client.writer.get_extra_info('peername'))
        client_info += "transaction id: 0x{:x}, protocol id: 0x{:x}," \
                       "len_field: {}, unit: 0x{:x}, ".format(
                        req.tran_id, req.proto_id, req.len_field, req.unit)
        client_info += "function code: 0x{:x}, data length: {} bytes".format(
                        req.fcode, len(req.data))
        print(client_info)

    def _have_modbus_response(self, req, fcode, data):
        return modbus_response(req, fcode, data)

    def _have_response_frame(self, res):
        buf = res.tran_id.to_bytes(length=2, byteorder='big')
        buf += res.proto_id.to_bytes(length=2, byteorder='big')
        buf += res.len_field.to_bytes(length=2, byteorder='big')
        buf += res.unit.to_bytes(length=1, byteorder='big')
        buf += res.fcode.to_bytes(length=1, byteorder='big')
        buf += res.data
        return buf

    async def _handle_transaction(self, client, buf):
        if not self._frame_ready(buf):
            return -1

        req = self._have_modbus_request(buf)
        self._print_client(client, req)

        if not self._check_header(req):
            return -1

        err = check_pdu(req.fcode, req.data)
        if err is not None:
            res_fcode, res_data = have_modbus_exception(req.fcode, err)
        else:
            res_fcode, res_data = func_dict[req.fcode](req.fcode, req.data)
        res = self._have_modbus_response(req, res_fcode, res_data)

        res_frame = self._have_response_frame(res)
        client.writer.write(res_frame)

        return 0

    async def _handle_client(self, client):
        buf = await client.reader.read(MODBUS_TCP_MAX_BUF_LEN)
        if buf is not None and len(buf) > 0:
            client.stop_timing()
            err = await self._handle_transaction(client, buf)
            if err != 0:
                client.close()
                return None
            else:
                client.start_timing()
        elif client.is_timeout():
            client.close()
            return None

        self.loop.create_task(self._handle_client(client))

    async def _run_server(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print("New client from {}".format(addr))
        client = modbus_client(reader, writer)
        self.loop.create_task(self._handle_client(client))

    def run(self):
        self.loop = asyncio.new_event_loop()
        coro = asyncio.start_server(self._run_server, self.host, self.port)
        self.loop.run_until_complete(coro)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.close()

    def close(self):
        self.loop.close()

    def __del__(self):
        self.close()

class modbus_tls_request(modbus_request):
    def parse_request(self, buf):
        self.fcode = int.from_bytes(buf[0:1], byteorder='big')
        self.data = buf[1:]

class modbus_tls_response(modbus_response):
    def build_response(self, req, fcode, data):
        self.fcode = fcode
        self.data = data

class modbus_tls_server(modbus_server):
    def __init__(self, host='localhost', port=8020, cert=None, key=None):
        self.host = host
        self.port = port
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(cert, key)

    def _is_this_unit(self, unit):
        return True

    def _frame_ready(self, buf):
        if len(buf) < 2:
            return False
        return True

    def _check_header(self, req):
            return True

    def _have_modbus_request(self, buf):
        return modbus_tls_request(buf)

    def _print_client(self, client, req):
        client_info = "Client {} ".format(client.writer.get_extra_info('peername'))
        client_info += "function code: 0x{:x}, data length: {} bytes".format(
                        req.fcode, len(req.data))
        print(client_info)

    def _have_modbus_response(self, req, fcode, data):
        return modbus_tls_response(req, fcode, data)

    def _have_response_frame(self, res):
        buf = res.fcode.to_bytes(length=1, byteorder='big')
        buf += res.data
        return buf

    def run(self):
        self.loop = asyncio.new_event_loop()
        coro = asyncio.start_server(self._run_server, self.host, self.port, ssl=self.context)
        self.loop.run_until_complete(coro)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.close()


if __name__ == '__main__':
    server = modbus_server()
    print("MODBUS server listens on {}:{}".format(server.host, server.port))
    server.run()
    print("MODBUS server closed")
