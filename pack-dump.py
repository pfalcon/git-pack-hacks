# This tool allows to dump contents of git pack, similarly to
# "git verify-pack -v", but unlike it, doesn't require .idx
# file, only a pack itself.
import sys
import binascii
from dulwich import pack
from dulwich import objects
from dulwich.objects import sha_to_hex
from pprint import pprint

OBJ_TYPES = {
    1: "OBJ_COMMIT",
    2: "OBJ_TREE",
    3: "OBJ_BLOB",
    4: "OBJ_TAG",
    6: "OBJ_OFS_DELTA",
    7: "OBJ_REF_DELTA",
}

p = pack.PackData(sys.argv[1])

def hexd(sha):
    return binascii.hexlify(sha.digest())

for e in p.iterobjects():
#    print(repr(e))
    print("Offset: %d\nType: %s(%d)" % (e[0], OBJ_TYPES[e[1]], e[1]))
    if e[1] in pack.DELTA_TYPES:
        print("Delta offset: %d (== %d)" % (-e[2][0], e[0] - e[2][0]))
        print(b''.join(e[2][1]))
    else:
        print(b''.join(e[2]))
    print()
