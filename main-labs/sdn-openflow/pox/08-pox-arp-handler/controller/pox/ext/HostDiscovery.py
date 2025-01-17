import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet
from pox.lib.util import dpidToStr

log = core.getLogger()
MAX_HOST = 4


class HostDiscovery:

    def __init__(self):

        # adds the hostDiscovery instance as a listener to OpenFlow-related events
        core.openflow.addListeners(self)

        # dictionary to store information about discovered hosts
        self.hosts = {}

        # dictionary to map switch identifiers to switch datapath IDs
        self.sw_id = {}

        # id to count connections_list
        self.id = 1

        # initializes fake MAC address for the gateway.
        self.fake_mac_gw = EthAddr("00:00:00:00:11:11")

    def _handle_ConnectionUp(self, event):

        # Associates the current connection ID with the switch ID
        self.sw_id[self.id] = event.dpid

        # increment connection ID
        self.id += 1

        print("host discovering")

        # Iterates through a max number of hosts
        for h in range(MAX_HOST):
            # Constructs an ARP request packet with a fake MAC address, and ARP request opcode
            arp_req = arp()
            arp_req.hwsrc = self.fake_mac_gw
            arp_req.opcode = arp.REQUEST
            arp_req.protosrc = IPAddr("10.0.0.100")
            arp_req.protodst = IPAddr(f"10.0.0.1{h}")

            # Constructs an Ethernet frame containing the ARP request packet
            ether = ethernet()
            ether.type = ethernet.ARP_TYPE
            ether.dst = EthAddr.BROADCAST
            ether.src = self.fake_mac_gw
            ether.payload = arp_req

            # Constructs an OpenFlow packet-out message
            msg = of.ofp_packet_out()
            msg.data = ether.pack()

            # Adds action to flood the ARP message to all ports and sends the message
            msg.actions.append(of.ofp_action_output(port=of.OFPP_ALL))
            event.connection.send(msg)

    def _handle_PacketIn(self, event):
        # Extracts the parsed Ethernet frame from the incoming packet
        eth_frame = event.parsed

        # Checks if the frame type is ARP and the destination MAC address is the fake mac
        if eth_frame.type == ethernet.ARP_TYPE and eth_frame.dst == self.fake_mac_gw:

            arp_message = eth_frame.payload

            # Checks if the ARP packet is a reply
            if arp_message.opcode == arp.REPLY:

                ip_host = arp_message.protosrc
                mac_host = arp_message.hwsrc

                if ip_host not in self.hosts:
                    # Stores the location of the host in the dictionary
                    self.hosts[ip_host] = {"switch": event.dpid, "port": event.port, "mac": mac_host}

                    # take the switch ID from linkDiscovery
                    dict_sw_id = self.sw_id
                    sw_id = [key for key, value in dict_sw_id.items() if value == event.dpid]

                    # convert sw_dpid in string type
                    sw_dpid = dpidToStr(self.hosts[ip_host]["switch"])
                    port = self.hosts[ip_host]["port"]

                    log.info(f"  ->  host {ip_host} is connected to switch {sw_id, sw_dpid} through switch port {port}")


def launch():
    core.registerNew(HostDiscovery)
