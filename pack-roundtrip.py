# This tool reads git pack, decoding it to git objects, and then writes
# them to another file, achieving round-trip (delta encoding is not used
# when writing new file).
import sys
import os
import binascii
from dulwich import pack
from dulwich import objects
from dulwich.objects import sha_to_hex
from pprint import pprint


def hexd(sha):
    return binascii.hexlify(sha.digest())


# If object is delta-encoded, resolve it to real object
def resolve_obj(e):
    if e.pack_type_num in pack.DELTA_TYPES:
        res = p.resolve_object(offset=e.offset, type=e.pack_type_num, obj=(e.delta_base, e.decomp_chunks))
        e.obj_type_num = res[0]
        e.obj_chunks = res[1]
        e.delta_base = None
    return e


def map_object_for_write(e):
    #print(e)
    # Need to resolve object, just to calculate its SHA1
    e = resolve_obj(e)
    return e.sha_file()

p = pack.PackData(sys.argv[1])

f = open("out.pack", "wb")
obj_map, check_sha = pack.write_pack_objects(f, [(map_object_for_write(e), None) for e in p._iter_unpacked()])
f.close()

pack_sha = binascii.hexlify(check_sha).decode("ascii")

os.rename("out.pack", "out-%s.pack" % pack_sha)

entries = [(k, v[0], v[1]) for (k, v) in obj_map.items()]
entries.sort()

with open("out-%s.idx" % pack_sha, "wb") as f:
    pack.write_pack_index_v2(f, entries, check_sha)
