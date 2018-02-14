#! /usr/bin/python3
# -*- coding: utf-8 -*-

'''
  weatherd3.py
  Copyright (C) 2018 Andreas Frisch <fraxinas@schaffenburg.org>

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or (at
  your option) any later version.

  This program is distributed in the hope that it will be useful, but
  WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
  General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
  USA.
'''

import sys
import json
import asyncio
from aiohttp import web


class Weatherd():
    Unit_converter = {
        "mph_to_kmh": lambda v: (v*1.60934),
        "F_to_C": lambda t: ((t-32) / 1.8),
        "inch_to_mm": lambda h: (h*25.4),
        "inHg_to_hPa": lambda h: (h*33.8637526)
    }

    def __init__(self):
        cfg_file = sys.path[0] + '/config.json'
        try:
            with open(cfg_file) as json_data_file:
                self.cfg = json.load(json_data_file)

        except FileNotFoundError:
            message = "Couldn't open the config file " + cfg_file
            print(message, sys.exc_info()[0])
            sys.exit(0)

        self.previous_values = {}

    async def process_values(self, query):
        sequence = ""
        for obj in self.cfg["objects"]:
            sensor = obj["sensor"]
            group = obj["knx_group"]
            debug_msg = "%s->%s" % (sensor, group)

            if sensor in query and obj["enabled"]:
                try:
                    value = float(query[sensor])
                    debug_msg += " numeric value: {0:g}".format(value)
                    conversion = obj["conversion"]
                    if conversion and conversion in self.Unit_converter:
                        value = round(self.Unit_converter[conversion](value), 2)
                        debug_msg += "^={0:g}".format(value)

                    if group in self.previous_values:
                        hysteresis = obj["hysteresis"]
                        prev_val = self.previous_values[group]
                        if obj["hysteresis"]:
                            if abs(value - prev_val) <= hysteresis:
                                print("{0}-{1:g}<{2:g} hysteresis, ignored!".
                                      format(debug_msg, prev_val, hysteresis))
                                continue
                        elif prev_val == value:
                            print(debug_msg, "unchanged, ignored!")
                            continue
                    sequence += '<object id="%s" value="%.2f"/>' % (group, value)

                except ValueError:
                    value = query[sensor]
                    debug_msg += " non-numeric value:", value
                    if group in self.previous_values and value == self.previous_values[group]:
                        print(debug_msg, "unchanged, ignored!")
                        continue
                    sequence += '<object id="%s" value="%s"/>' % (group, value)
                self.previous_values[group] = value
                print(debug_msg)

        if sequence:
            if sequence:
                xml = '<write>' + sequence + '</write>\n\x04'
                print("sending", xml[:-2])
                self.knx_writer.write(xml.encode(encoding='utf_8'))
                self.knx_writer.drain()
                data = await asyncio.wait_for(self.knx_reader.readline(), timeout=10.0)
                print("received {!r}".format(data.decode()))

    async def handle(self, request):
        print("handle: ", str(request.rel_url.query))
        await self.process_values(request.rel_url.query)
        return web.Response(text="success\n")

    async def linknx_client(self, loop, knxcfg):
        self.knx_reader, self.knx_writer = await asyncio.open_connection(
            knxcfg["host"], knxcfg["port"], loop=loop)

    def run(self, argv):
        print("running...")
        loop = asyncio.get_event_loop()

        knx_server = loop.run_until_complete(self.linknx_client(loop, self.cfg["linknx"]))

        ws_app = web.Application(debug=True)
        ws_app.router.add_get('/weatherstation/{name}', self.handle)
        ws_handler = ws_app.make_handler()
        scfg = self.cfg["sys"]
        ws_coro = loop.create_server(ws_handler, scfg["listenHost"], scfg["listenPort"])
        ws_server = loop.run_until_complete(ws_coro)

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            ws_server.close()
            loop.run_until_complete(ws_app.shutdown())
            loop.run_until_complete(ws_handler.shutdown(2.0))
            loop.run_until_complete(ws_app.cleanup())

if __name__ == "__main__":
    weatherd = Weatherd()
    weatherd.run(sys.argv[1:])
