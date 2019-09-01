#!/bin/env python3

from enum import IntEnum
from math import ceil
from random import randint
from time import time
import asyncio, socket

MODBUS_TCP_MAX_BUF_LEN = 253 + 7

class modbus_exception(IntEnum):
    ILLEGAL_FUNCTION = 0x1
    ILLEGAL_DATA_ADDRESS = 0x2
    ILLEGAL_DATA_VALUE = 0x3

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

def have_modbus_exception(req, fcode, error):
    res_fcode = fcode + 0x80
    res_data = error.to_bytes(length=1, byteorder='big')
    return res_fcode, res_data

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

def have_addr_cnt(data):
    addr = int.from_bytes(data[0:2], byteorder='big')
    cnt = int.from_bytes(data[2:4], byteorder='big')
    return addr, cnt

def read_coils(fcode, data):
    addr, cnt = have_addr_cnt(data)
    if cnt < 0 or cnt > 0x07D0:
        err = modbus_exception.ILLEGAL_DATA_VALUE
        return have_modbus_exception(fcode, err)

    if addr > 0xFFFF or addr + cnt - 1 > 0xFFFF:
        err = modbus_exception.ILLEGAL_DATA_ADDRESS
        return have_modbus_exception(fcode, err)

    byte_cnt = ceil(cnt / 8)
    res_data = byte_cnt.to_bytes(length=1, byteorder='big')
    val = randint(0, pow(2, cnt) - 1)
    res_data += val.to_bytes(length=byte_cnt, byteorder='big')

    return fcode, res_data

def read_discrete_inputs(fcode, data):
    return read_coils(fcode, data)

def read_holding_registers(fcode, data):
    addr, cnt = have_addr_cnt(data)
    if cnt < 0 or cnt > 125:
        err = modbus_exception.ILLEGAL_DATA_VALUE
        return have_modbus_exception(fcode)

    if addr > 0xFFFF or addr + cnt - 1 > 0xFFFF:
        err = modbus_exception.ILLEGAL_DATA_ADDRESS
        return have_modbus_exception(fcode, err)

    byte_cnt = cnt * 2
    res_data = byte_cnt.to_bytes(length=1, byteorder='big')
    for i in range(cnt):
        val = randint(0, pow(2, 16) - 1)
        res_data += val.to_bytes(length=2, byteorder='big')

    return fcode, res_data

def read_input_registers(fcode, data):
    return read_holding_registers(fcode, data)

def have_addr_val(paylaod):
    addr = int.from_bytes(data[0:2], byteorder='big')
    val = int.from_bytes(data[2:4], byteorder='big')
    return addr, val

def write_single_coil(fcode, data):
    addr, val = have_addr_val(data)
    if val != 0x0 and val != 0xFF00:
        err = modbus_exception.ILLEGAL_DATA_VALUE
        return have_modbus_exception(fcode, err)

    return fcode, data

def write_single_register(fcode, data):
    addr, val = have_addr_val(data)

    return fcode, data

def have_addr_cnt_vals(data):
    addr = int.from_bytes(data[0:2], byteorder='big')
    cnt = int.from_bytes(data[2:4], byteorder='big')
    byte_cnt = int.from_bytes(data[4:5], byteorder='big')
    vals = int.from_bytes(data[5:], byteorder='big')
    return addr, cnt, byte_cnt, vals

def write_multiple_coils(fcode, data):
    addr, cnt, byte_cnt, vals = have_addr_cnt_vals(data)
    if cnt < 0 or cnt > 0x07B0 or \
       ceil(cnt / 8) != byte_cnt or \
       byte_cnt != len(vals):
        err = modbus_exception.ILLEGAL_DATA_VALUE
        return have_modbus_exception(fcode, err)

    if addr > 0xFFFF or addr + cnt - 1 > 0xFFFF:
        err = modbus_exception.ILLEGAL_DATA_ADDRESS
        return have_modbus_exception(fcode, err)

    res_data = addr.to_bytes(length=2, byteorder='big')
    res_data += cnt.to_bytes(length=2, byteorder='big')
    return fcode, res_data

def write_multiple_registers(fcode, data):
    addr, cnt, byte_cnt, vals = have_addr_cnt_vals(data)
    if cnt < 0 or cnt > 0x7B or \
       cnt / 2 != byte_cnt or \
       byte_cnt != len(vals):
        err = modbus_exception.ILLEGAL_DATA_VALUE
        return have_modbus_exception(fcode, err)

    if addr > 0xFFFF or addr + cnt - 1 > 0xFFFF:
        err = modbus_exception.ILLEGAL_DATA_ADDRESS
        return have_modbus_exception(fcode, err)

    res_data = addr.to_bytes(length=2, byteorder='big')
    res_data += cnt.to_bytes(length=2, byteorder='big')
    return fcode, res_data

func_dict = {
    0x1:  read_coils,
    0x2:  read_discrete_inputs,
    0x3:  read_holding_registers,
    0x4:  read_input_registers, 
    0x5:  write_single_coil,
    0x6:  write_single_register,
    0xf:  write_multiple_coils,
    0x10: write_multiple_registers,
}

def check_fcode(fcode):
    try:
        func_dict[fcode]
        res = True
    except KeyError:
        res = False

    return res

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
    def __init__(self, ip='0.0.0.0', port=5020, unit=1):
        self.svr_ip = ip
        self.svr_port = port
        self.unit = unit

    def is_this_unit(self, unit):
        if unit == 0 or unit == self.unit:
            return True
        else:
            return False

    async def send_response(self, client, res):
        buf = res.tran_id.to_bytes(length=2, byteorder='big')
        buf += res.proto_id.to_bytes(length=2, byteorder='big')
        buf += res.len_field.to_bytes(length=2, byteorder='big')
        buf += res.unit.to_bytes(length=1, byteorder='big')
        buf += res.fcode.to_bytes(length=1, byteorder='big')
        buf += res.data

        client.writer.write(buf)

    async def handle_transaction(self, client, buf):
        if len(buf) < 8:
            return -1

        req = modbus_request(buf)

        print("Client {} transaction id: 0x{:x}, protocol id: 0x{:x}, "
              "len_field: {}, unit: 0x{:x}, function code: 0x{:x}, "
              "data length: {} bytes".format(client.writer.get_extra_info('peername'),
              req.tran_id, req.proto_id, req.len_field, req.unit, req.fcode,
              len(req.data)))

        if req.proto_id != 0 or \
           req.len_field != 1 + 1 + len(req.data) or \
           not self.is_this_unit(req.unit):
            return -1

        err = check_pdu(req.fcode, req.data)
        if err is not None:
            res_fcode, res_data = have_modbus_exception(req.fcode, err)
        else:
            res_fcode, res_data = func_dict[req.fcode](req.fcode, req.data)
        res = modbus_response(req, res_fcode, res_data)

        await self.send_response(client, res)

        return 0

    async def handle_client(self, client):
        buf = await client.reader.read(MODBUS_TCP_MAX_BUF_LEN)
        if buf is not None and len(buf) > 0:
            client.stop_timing()
            err = await self.handle_transaction(client, buf)
            if err != 0:
                client.close()
                return None
            else:
                client.start_timing()
        elif client.is_timeout():
            client.close()
            return None

        self.loop.create_task(self.handle_client(client))

    async def _run_server(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print("New client from {}".format(addr))
        client = modbus_client(reader, writer)
        self.loop.create_task(self.handle_client(client))

    def run(self):
        self.loop = asyncio.get_event_loop()
        coro = asyncio.start_server(self._run_server, self.svr_ip, self.svr_port, loop=self.loop)
        self.loop.run_until_complete(coro)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.close()

    def close(self):
        self.loop.close()

    def __del__(self):
        self.close()

if __name__ == '__main__':
    server = modbus_server()
    print("MODBUS server listens on {}:{}".format(server.svr_ip, server.svr_port))
    server.run()
    print("MODBUS server closed")
