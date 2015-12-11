# Transcode a git pack, applying a transformation to blob objects,
# and recalculating SHA IDs of all dependent objects, up to commits.
import sys
import os
import binascii
from dulwich import pack
from dulwich import objects
from dulwich.objects import sha_to_hex
from pprint import pprint


def encrypt(bts):
    return bytes([255 - b for b in bts])

def encrypt_chunks(l):
    return [encrypt(x) for x in l]

def hexd(sha):
    return binascii.hexlify(sha.digest())


#print(encrypt_chunks([b"\x80\x80", b"abc"]))

# Mappings from non-encrypted to encrypted object ids
BLOB_MAP = {}
TREE_MAP = {}
COMMIT_MAP = {}

# Cached input objects
OBJ_LIST = []

# Cached output objects
BLOB_STORE = {}
TREE_STORE = {}
COMMIT_STORE = {}

COMMIT_STORE_IN = {}

# If object is delta-encoded, resolve it to real object
def resolve_obj(e):
    if e.pack_type_num in pack.DELTA_TYPES:
        res = p.resolve_object(offset=e.offset, type=e.pack_type_num, obj=(e.delta_base, e.decomp_chunks))
        e.obj_type_num = res[0]
        e.obj_chunks = res[1]
        e.delta_base = None
    return e


p = pack.PackData(sys.argv[1])
print("Loading pack to memory, resolving deltas")
for e in p._iter_unpacked():
#    print(repr(e))
    e = resolve_obj(e)
    e = e.sha_file()
    OBJ_LIST.append(e)
    if isinstance(e, objects.Commit):
        COMMIT_STORE_IN[hexd(e.sha())] = e

for e in OBJ_LIST:
    print(e)


print("Mapping blobs")
for e in OBJ_LIST:
#    print(repr(e))
    if isinstance(e, objects.Blob):
        print(repr(e))
        org_sha = hexd(e.sha())
        cry_blob = objects.Blob()
        cry_blob.chunked = encrypt_chunks(e.chunked)
        cry_sha = hexd(cry_blob.sha())
        print("%s -> %s" % (org_sha, cry_sha))
        BLOB_MAP[org_sha] = cry_sha
        BLOB_STORE[cry_sha] = cry_blob


print("\nMapping trees")
for e in OBJ_LIST:
#    print(repr(e), type(e))
    if isinstance(e, objects.Tree):
        print(repr(e))
#        assert len(e[2]) == 1
        org_sha = hexd(e.sha())
        new_tree = objects.Tree()
        for name, mode, hexsha in e.iteritems():
            new_tree.add(name, mode, BLOB_MAP[hexsha])
        cry_sha = hexd(new_tree.sha())
        print(org_sha, cry_sha)
        TREE_MAP[org_sha] = cry_sha
        TREE_STORE[cry_sha] = new_tree
        print()

def map_commit(sha):
    if sha in COMMIT_MAP:
        return COMMIT_MAP[sha]
    commit = COMMIT_STORE_IN[sha]
    new_parents = [map_commit(c) for c in commit.parents]
    print("old parents: %s, new: %s" % (commit.parents, new_parents))
    new_commit = commit.copy()
    new_commit.parents = new_parents
    new_commit.tree = TREE_MAP[commit.tree]
    new_sha = hexd(new_commit.sha())
    COMMIT_MAP[sha] = new_sha
    COMMIT_STORE[new_sha] = new_commit
    print("%s -> %s" % (sha, new_sha))
    return new_sha


print("\nMapping commits")
for e in OBJ_LIST:
    if isinstance(e, objects.Commit):
        print(repr(e))
        print(e.__dict__)
        print(hexd(e.sha()))
        map_commit(hexd(e.sha()))


out_list = []
for e in OBJ_LIST:
    sha = hexd(e.sha())
    if isinstance(e, objects.Blob):
        e = BLOB_STORE[BLOB_MAP[sha]]
    elif isinstance(e, objects.Tree):
        e = TREE_STORE[TREE_MAP[sha]]
    elif isinstance(e, objects.Commit):
        e = COMMIT_STORE[COMMIT_MAP[sha]]
    out_list.append((e, None))


f = open("crypt.pack", "wb")
obj_map, check_sha = pack.write_pack_objects(f, out_list)
f.close()

pack_sha = binascii.hexlify(check_sha).decode("ascii")

os.rename("crypt.pack", "crypt-%s.pack" % pack_sha)

entries = [(k, v[0], v[1]) for (k, v) in obj_map.items()]
entries.sort()

with open("crypt-%s.idx" % pack_sha, "wb") as f:
    pack.write_pack_index_v2(f, entries, check_sha)
