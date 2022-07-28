def dht_hash(text, seed=0, maximum=2**10):
    """ FNV-1a Hash Function. """
    fnv_prime = 16777619
    offset_basis = 2166136261
    h = offset_basis + seed
    for char in text:
        h = h ^ ord(char)
        h = h * fnv_prime
    return h % maximum


def contains(begin, end, node):
    """ Check node is contained between begin and end in a ring. """
    #TODO
    if begin < node <= end:
        return True
    if end < begin:
        if begin < node:
            return True
        elif node <= end:
            return True
    return False