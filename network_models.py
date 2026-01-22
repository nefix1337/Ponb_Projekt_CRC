"""Modele sieciowe - Node i Packet."""

class Packet:
    """Pakiet danych w sieci."""
    def __init__(self, sender_id, receiver_id, message, frame_bits, crc_poly):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.message = message
        self.frame_bits = frame_bits
        self.crc_poly = crc_poly
        self.status = 'sent'
        self.delay = 0.0
        self.crc_valid = None


class Node:
    """Węzeł (komputer) w sieci."""
    def __init__(self, node_id, port):
        self.node_id = node_id
        self.port = port
        self.errors = {'BIT_FLIP': False, 'DROP_PACKET': False, 'DELAY_PACKET': False}
        self.packets_history = []
        self.last_message = None
    
    def set_error(self, error_type, enabled):
        """Włącz/wyłącz błąd."""
        self.errors[error_type] = enabled
    
    def disable_all_errors(self):
        """Wyłącz wszystkie błędy."""
        for e in self.errors:
            self.errors[e] = False
    
    def add_packet(self, packet):
        """Dodaj pakiet do historii."""
        self.packets_history.append(packet)
