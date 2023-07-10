# Key-value Store

We design and implement a key-value store. Values have a variable length and
are stored under a string of characters that consitute a key. A value and its
key constitute an item.

The query interface is 'CRUD': items can be created, retrieved, updated, and
deleted.

Items are stored in sorted-string tables (SST). SSTs store items in sorted
order by key. An in-memory index maps keys to their location (which SST, and
position within SST). The index is sparse, it stores the location of the first
item in a block of a few kilobytes.

To efficiently write sorted key-value pairs to disk, they are first written to
an in-memory search tree called a memtable, which stores keys in sorted order.

Once the memtable reaches 1MB in size, it is written to disk in a new SST and a
new (initially empty memtable is created).

To retrieve an item, the memtable is searched first. If the item is not found
in the memtable, SSTs are searched from the most recent to the least recent.
For each SST that is searched, the candidate block location is retrieved from
the index, the block is retrieved from disk, then and its items are scanned
sequentially.

To avoid unnecessarily searching SSTs, each SST has a bloom filter that
indicates if an item is not present in the SST.

## SST segment structure

The SST is made of separate segments, stored on separate files on disk.

An SST segment contains a header, followed by a segment index, followed by a
sequence of records.

The segment header is stored at offset 0 and contains the following information
(offset are in bytes):

* the version number at offset 0, stored in 8 bytes
* the number of records at offset 8, stored in 8 bytes
* the offset of the first record, at offset 16, stored in 8 bytes.

The segment index is stored at offset 24, and takes a variable amount of space.

The first segment record is stored at the offset indicated by the the 8-byte
number stored at offset 16. Records are stored sequentially and take a variable
amount of space.

## Index structure

The index contains the key and file offset for a subset of the segment records.
An index item is made for one record out of 1,000.

The index contains the following:

* the number of index elements (4 bytes) at index offset 0
* a sequence of index elements (variable number of bytes) at index offset 4

An index element contains:

* the key size (1 byte) at element offset 0
* the key (variable number of bytes) at element offset 1
* the record offset (8 bytes)

## Record structure

A record is made of the following elements (in order):

* record size at offset 0 (stored in 4 bytes)
* key size at offset 4 (store in 1 byte)
* key at offset 5 (stored in a variable number of bytes)
* value (stored in a variable number of bytes)

The key size is limited to 256 characters (because the size is stored in 1
byte).

## Memtable

The memtable is implemented as a red-black tree, a type of balanced binary
tree. Each tree node stores the key as a variable length character string and
the value as a variable length byte string.

The tree that stores the memtable is append and update only, nodes are never
deleted, except when the whole tree is destroyed. When an already
existing key is added to the tree, the value of the node with the matching key
is updated. When a key is deleted, its value is set to null (tombstone) and it
is skipped when the memtable is written to disk.
