import heapq
from collections import Counter
from typing import Dict, Tuple


class _Node:
    """
    A node in the Huffman tree.
    
    Attributes:
        freq (int): Frequency of the symbol(s) represented by this node.
        symbol (bytes or None): The byte symbol, if this is a leaf node.
        left (_Node): Left child.
        right (_Node): Right child.
    """
    def __init__(self, freq: int, symbol: bytes = None, left=None, right=None):
        self.freq = freq
        self.symbol = symbol
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq


async def _build_tree(data: bytes) -> _Node:
    """
    Build a Huffman tree from the input data.
    
    Args:
        data (bytes): The input byte string.
    
    Returns:
        _Node: The root of the constructed Huffman tree.
    """
    freq = Counter(data)
    heap = [_Node(f, bytes([b])) for b, f in freq.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        heapq.heappush(heap, _Node(left.freq + right.freq, None, left, right))

    return heap[0]


async def _build_codes(node: _Node) -> Dict[bytes, str]:
    """
    Build Huffman codes from a Huffman tree.

    Args:
        node (_Node): Root of the Huffman tree.

    Returns:
        Dict[bytes, str]: A mapping from byte symbols to their Huffman bitstrings.
    """
    codes = {}

    async def traverse(n, path: str):
        if n.symbol is not None:
            codes[n.symbol] = path
            return
        await traverse(n.left, path + "0")
        await traverse(n.right, path + "1")

    await traverse(node, "")
    return codes


async def _encode_bits(data: bytes, codes: Dict[bytes, str]) -> Tuple[bytes, int]:
    """
    Encode the input data into a bitstring using the Huffman codes.

    Args:
        data (bytes): Original data to encode.
        codes (Dict[bytes, str]): Huffman codes for each byte.

    Returns:
        Tuple[bytes, int]: Tuple of encoded bytes and number of zero-padding bits added.
    """
    bitstring = "".join(codes[bytes([b])] for b in data)
    padding = (8 - len(bitstring) % 8) % 8
    bitstring += "0" * padding
    encoded = int(bitstring, 2).to_bytes(len(bitstring) // 8, "big")
    return encoded, padding


async def huffman_encode_async(data: bytes) -> Tuple[bytes, Dict[bytes, str], int]:
    """
    Perform Huffman encoding asynchronously.

    Args:
        data (bytes): Data to be encoded.

    Returns:
        Tuple[bytes, Dict[bytes, str], int]: Encoded bytes, Huffman code table, and padding length.
    """
    tree = await _build_tree(data)
    codes = await _build_codes(tree)
    encoded, padding = await _encode_bits(data, codes)
    return encoded, codes, padding
