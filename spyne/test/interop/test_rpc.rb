#!/usr/bin/ruby

class InteropTest
  require 'soap/rpc/driver'

  def initialize()
    ws_url='http://127.0.0.1:9754/'
    ws_ns='InteropService.InteropService'
    @conn = SOAP::RPC::Driver.new(ws_url, ws_ns)
  end

  def echo_int(i)
    @conn.add_method("echo_integer", "i")
    @conn.echo_integer(i)
  end

  def echo_string(s)
    @conn.add_method("echo_string", "s")
    @conn.echo_string(s)
  end
end

ws = InteropTest.new()

puts ws.echo_string("OK")
puts ws.echo_int(0)
