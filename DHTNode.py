""" Chord DHT node implementation. """
import socket
import threading
import logging
import pickle
from utils import dht_hash, contains


class FingerTable:
    """Finger Table."""

    def __init__(self, node_id, node_addr, m_bits=10):
        """Initialize Finger Table."""
        self.node_id = node_id
        self.node_addr = node_addr
        self.m_bits = m_bits
        self.finger_table = [(node_id, node_addr)] * m_bits

    def fill(self, node_id, node_addr):
        """Fill all entries of finger_table with node_id, node_addr."""
        n_entries = self.m_bits
        i = 0
        while i < n_entries:
            self.finger_table[i] = (node_id, node_addr)
            i += 1

    def update(self, index, node_id, node_addr):
        """Update index of table with node_id and node_addr."""
        len_finger_table = len(self.finger_table)

        if (len_finger_table > index - 1):
            self.finger_table.pop(index - 1)

        self.finger_table.insert(index - 1, (node_id, node_addr))

    def find(self, identification):
        """Get node address of closest preceding node (in finger table) of identification."""
        len_finger_table = len(self.finger_table)
        i = 0
        while i < len_finger_table:
            if (contains(self.node_id, self.finger_table[i][0], identification)):
                return self.finger_table[i-1][1]
            i += 1
        return self.finger_table[-1][1]

    def refresh(self):
        """Retrieve finger table entries."""
        # entry node n will contain successor((n+2**(i-1))mod 2**m) -> m = m_bits | First i must be = 0
        # (i + 1, ... ) -> Need to put because of assert
        entries = []
        i = 0
        while i < len(self.finger_table):
            entries.append((i + 1,(self.node_id + 2 ** i) % 2**self.m_bits, self.finger_table[i][1]))
            i += 1
        return entries

    def getIdxFromId(self, id):
        # Need to compare id with (node_id + 2**idx) % 2**len_finger_table) len_finger_table = m_bits -> successor((n+2**(i-1))mod 2**m)
        len_finger_table = len(self.finger_table)

        for idx in range(len_finger_table):
            if id == ((self.node_id + 2**idx) % 2**len_finger_table):
                return idx + 1
        return None

    def __repr__(self):
        return str(self.finger_table)

    @property
    def as_list(self):
        """return the finger table as a list of tuples: (identifier, (host, port)).
        NOTE: list index 0 corresponds to finger_table index 1
        """
        return self.finger_table


class DHTNode(threading.Thread):
    """DHT Node Agent."""

    def __init__(self, address, dht_address=None, timeout=3):
        """Constructor

        Parameters:
            address: self's address
            dht_address: address of a node in the DHT
            timeout: impacts how often stabilize algorithm is carried out
        """
        threading.Thread.__init__(self)
        self.done = False
        self.identification = dht_hash(address.__str__())
        self.addr = address  # My address
        self.dht_address = dht_address  # Address of the initial Node
        if dht_address is None:
            self.inside_dht = True
            # I'm my own successor
            self.successor_id = self.identification
            self.successor_addr = address
            self.predecessor_id = None
            self.predecessor_addr = None
        else:
            self.inside_dht = False
            self.successor_id = None
            self.successor_addr = None
            self.predecessor_id = None
            self.predecessor_addr = None

        self.finger_table = FingerTable(
            self.identification, self.addr
        )  # TODO create finger_table

        self.keystore = {}  # Where all data is stored
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)
        self.logger = logging.getLogger("Node {}".format(self.identification))

    def send(self, address, msg):
        """Send msg to address."""
        payload = pickle.dumps(msg)
        self.socket.sendto(payload, address)

    def recv(self):
        """Retrieve msg payload and from address."""
        try:
            payload, addr = self.socket.recvfrom(1024)
        except socket.timeout:
            return None, None

        if len(payload) == 0:
            return None, addr
        return payload, addr

    def node_join(self, args):
        """Process JOIN_REQ message.

        Parameters:
            args (dict): addr and id of the node trying to join
        """

        self.logger.debug("Node join: %s", args)
        addr = args["addr"]
        identification = args["id"]
        if self.identification == self.successor_id:  # I'm the only node in the DHT
            self.successor_id = identification
            self.successor_addr = addr
            # TODO update finger table
            self.finger_table.update(1, self.successor_id, self.successor_addr)
            args = {"successor_id": self.identification, "successor_addr": self.addr}
            self.send(addr, {"method": "JOIN_REP", "args": args})
        elif contains(self.identification, self.successor_id, identification):
            args = {
                "successor_id": self.successor_id,
                "successor_addr": self.successor_addr,
            }
            self.successor_id = identification
            self.successor_addr = addr
            # TODO update finger table
            self.finger_table.update(1, self.successor_id, self.successor_addr)
            self.send(addr, {"method": "JOIN_REP", "args": args})
        else:
            self.logger.debug("Find Successor(%d)", args["id"])
            self.send(self.successor_addr, {"method": "JOIN_REQ", "args": args})
        self.logger.info(self)

    def get_successor(self, args):
        """Process SUCCESSOR message.

        Parameters:
            args (dict): addr and id of the node asking
        """

        self.logger.debug("Get successor: %s", args)
        # TODO Implement processing of SUCCESSOR message
        node_id = args["id"]
        addr = args["from"]

        if contains(self.identification, self.successor_id, node_id):
            args = {
                "req_id": node_id,
                "successor_id": self.successor_id,
                "successor_addr": self.successor_addr,
            }
            self.send(addr, {"method": "SUCCESSOR_REP", "args": args})
        elif (
            self.predecessor_id is None
            or contains(self.predecessor_id, self.identification, node_id)
        ):
            args = {
                "req_id": node_id,
                "successor_id": self.identification,
                "successor_addr": self.addr,
            }
            self.send(addr, {"method": "SUCCESSOR_REP", "args": args})
        else:
            args = {"id": node_id, "from": addr}
            self.send(self.successor_addr, {"method": "SUCCESSOR", "args": args})

    def notify(self, args):
        """Process NOTIFY message.
            Updates predecessor pointers.

        Parameters:
            args (dict): id and addr of the predecessor node
        """

        self.logger.debug("Notify: %s", args)
        if self.predecessor_id is None or contains(
            self.predecessor_id, self.identification, args["predecessor_id"]
        ):
            self.predecessor_id = args["predecessor_id"]
            self.predecessor_addr = args["predecessor_addr"]
        self.logger.info(self)

    def stabilize(self, from_id, addr):
        """Process STABILIZE protocol.
            Updates all successor pointers.

        Parameters:
            from_id: id of the predecessor of node with address addr
            addr: address of the node sending stabilize message
        """

        self.logger.debug("Stabilize: %s %s", from_id, addr)
        if from_id is not None and contains(
            self.identification, self.successor_id, from_id
        ):
            # Update our successor
            self.successor_id = from_id
            self.successor_addr = addr
            # TODO update finger table
            self.finger_table.update(1, self.successor_id, self.successor_addr)

        # notify successor of our existence, so it can update its predecessor record
        args = {"predecessor_id": self.identification, "predecessor_addr": self.addr}
        self.send(self.successor_addr, {"method": "NOTIFY", "args": args})

        # TODO refresh finger_table
        entries_lst = self.finger_table.refresh()
        for entry in entries_lst:
            self.send(
                entry[2],
                {"method": "SUCCESSOR", "args": {"id": entry[1], "from": self.addr}},
            )

    def put(self, key, value, address):
        """Store value in DHT.

        Parameters:
        key: key of the data
        value: data to be stored
        address: address where to send ack/nack
        """
        key_hash = dht_hash(key)
        self.logger.debug("Put: %s %s", key, key_hash)

        # TODO Replace next code:
        # If my responsibility
        if contains(self.predecessor_id, self.identification, key_hash):
            if key in self.keystore:                                        
                self.send(address, {"method": "NACK"})              
            else:
                self.keystore[key] = value  
                self.send(address, {"method": "ACK"}) 
        # If next node's responsibility
        elif contains(self.identification,self.successor_id,key_hash):
            args = {"key": key, "value" : value, "from": address}
            self.send(self.successor_addr, {"method": "PUT", "args": args})
        # Send to the closest preceding to the id
        else:
            args = {"key": key, "value": value, "from": address}
            self.send(self.finger_table.find(key_hash), {"method": "PUT", "args": args}) 

    def get(self, key, address):
        """Retrieve value from DHT.

        Parameters:
        key: key of the data
        address: address where to send ack/nack
        """
        key_hash = dht_hash(key)
        self.logger.debug("Get: %s %s", key, key_hash)

        # TODO Replace next code:
        # If my responsibility
        if contains(self.predecessor_id, self.identification, key_hash):
            if key not in self.keystore.keys():
                self.send(address, {"method": "NACK"})
            else:
                value = self.keystore[key]
                self.send(address, {'method': 'ACK', "args": value})
        # If next node's responsibility
        elif contains(self.identification, self.successor_id, key_hash):
            args = {"key": key, "from": address}
            self.send(self.successor_addr, {"method": "GET", "args": args})
        # Send to the closest preceding to the id
        else:
            args = {"key": key, "from": address}
            self.send(self.finger_table.find(key_hash), {"method": "GET", "args": args})

    def run(self):
        self.socket.bind(self.addr)

        # Loop untiln joining the DHT
        while not self.inside_dht:
            join_msg = {
                "method": "JOIN_REQ",
                "args": {"addr": self.addr, "id": self.identification},
            }
            self.send(self.dht_address, join_msg)
            payload, addr = self.recv()
            if payload is not None:
                output = pickle.loads(payload)
                self.logger.debug("O: %s", output)
                if output["method"] == "JOIN_REP":
                    args = output["args"]
                    self.successor_id = args["successor_id"]
                    self.successor_addr = args["successor_addr"]
                    # TODO fill finger table
                    self.finger_table.fill(self.successor_id, self.successor_addr)
                    self.inside_dht = True
                    self.logger.info(self)

        while not self.done:
            payload, addr = self.recv()
            if payload is not None:
                output = pickle.loads(payload)
                self.logger.info("O: %s", output)
                if output["method"] == "JOIN_REQ":
                    self.node_join(output["args"])
                elif output["method"] == "NOTIFY":
                    self.notify(output["args"])
                elif output["method"] == "PUT":
                    self.put(
                        output["args"]["key"],
                        output["args"]["value"],
                        output["args"].get("from", addr),
                    )
                elif output["method"] == "GET":
                    self.get(output["args"]["key"], output["args"].get("from", addr))
                elif output["method"] == "PREDECESSOR":
                    # Reply with predecessor id
                    self.send(
                        addr, {"method": "STABILIZE", "args": self.predecessor_id}
                    )
                elif output["method"] == "SUCCESSOR":
                    # Reply with successor of id
                    self.get_successor(output["args"])
                elif output["method"] == "STABILIZE":
                    # Initiate stabilize protocol
                    self.stabilize(output["args"], addr)
                elif output["method"] == "SUCCESSOR_REP":
                    # TODO Implement processing of SUCCESSOR_REP
                    args = output["args"]
                    req_id = args["req_id"]
                    successor_id = args["successor_id"]
                    successor_addr = args["successor_addr"]
                    self.finger_table.update(
                        self.finger_table.getIdxFromId(req_id),
                        successor_id,
                        successor_addr,
                    )
            else:  # timeout occurred, lets run the stabilize algorithm
                # Ask successor for predecessor, to start the stabilize process
                self.send(self.successor_addr, {"method": "PREDECESSOR"})

    def __str__(self):
        return "Node ID: {}; DHT: {}; Successor: {}; Predecessor: {}; FingerTable: {}".format(
            self.identification,
            self.inside_dht,
            self.successor_id,
            self.predecessor_id,
            self.finger_table,
        )

    def __repr__(self):
        return self.__str__()
