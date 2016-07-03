#!/usr/bin/python
import hal, time
import logging
import serial
import struct
import crcmod

# setup log
log = logging.getLogger('')
log.setLevel(logging.DEBUG)

# create console handler and set level to info
log_format = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(log_format)
log.addHandler(ch)

# create file handler and set to debug
fh = logging.FileHandler('xbee.log')
fh.setFormatter(log_format)
log.addHandler(fh)

crc8_func = crcmod.predefined.mkPredefinedCrcFun("crc-8-maxim")

h = hal.component("xbee")
# these for control
h.newpin("pos", hal.HAL_FLOAT, hal.HAL_IN)
h.newparam("scale", hal.HAL_FLOAT, hal.HAL_RW)

# these for monitoring connection on bbb
h.newpin("rx-err", hal.HAL_U32, hal.HAL_OUT)
h.newpin("cksum-err", hal.HAL_U32, hal.HAL_OUT)

# these for monitoring connection on gondola
h.newpin("gond_batt", hal.HAL_U32, hal.HAL_OUT)
h.newpin("gond_rx_count", hal.HAL_U32, hal.HAL_OUT)
h.newpin("gond_err_count", hal.HAL_U32, hal.HAL_OUT)

log.info("scale = %d" % h['scale'])

serial_port=serial.Serial()
serial_port.port='/dev/ttyO1'
serial_port.timeout=0.05
serial_port.baudrate=57600
serial_port.open()
log.info("port opened")

h.ready()
log.info("hal ready")

def communicate(amount):
    bin = struct.pack('<B', amount)
    bin = struct.pack('<BB',amount, crc8_func(bin))
    serial_port.write(bin)

    response = serial_port.read(7)
    if response:
        batt, rx_count, err_count, cksum = struct.unpack('<HHHB', response)
        bin = struct.pack('<HHH', batt, rx_count, err_count)
        # check cksum
        if cksum == crc8_func(bin):
            h['gond_batt'] = batt
            h['gond_rx_count'] = rx_count
            h['gond_err_count'] = err_count
        else:
            h['cksum-err'] += 1
    else:
        h['rx-err'] += 1

try:
    while 1:
        time.sleep(0.05)
        val = h['pos'] * h['scale']
        if val > 180: #max angle is 180
            val = 180
        if val < 0:
            val = 0
        communicate(val)
except KeyboardInterrupt:
    raise SystemExit
    log.error("keyboard interrupt")
except Exception as e:
    log.error(e)