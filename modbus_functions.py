#!/bin/env python3

from math import ceil
from random import randint

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
