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

## Master table

The master table is made of a memtable, SST, and WAL that store information
about database namespaces:

* name of namespaces (i.e. tables)
* file path to SST segments (remember each segment is in a separate file)
* file path to WAL of each SST

Each namespace has several records (i.e. memtable nodes):

* Record with the key <namespace>-sst to store the SST paths (string of
  null-separated file paths).
* Record with the key <namespace>-wal to store the path of the WAL.

The files for each namespace are stored in a folder that bears the name of the
namespace.

How do we store the master table? The goal of the master table is to keep track
of what files store what segment, so how do we keep track of what files store
segments of the master table?

## Application startup

A user creates a database object by passing the name of a database file path.
This database base is effectively as "master namespace".

The database object allows performing the following actions:

* Create a namespace.
* Use a namespace (required to perform queries).
* Query a namespace.
* Delete a namespace.

To allow these actions, the database object contains:

* A memtable of the master table.
* An index of the master table.
* A file pointer to the master WAL.
* A memtable of the currently used namespace.
* An index of the first SST of the currently used namespace.
* A list of SST segments of the currently used namespace.
* A file pointer to the currently used namespace WAL.

## Data flow

### Write request

When an insert/update or delete is sent to the application, the following steps
occur:

1. Append command to write-ahead log.
2. Insert/update or delete memtable value for requested key.
3. If the size of the memtable exceeds a pre-determined size threshold, it is
   written to disk as an SST segment and an index is built for future queries.

### Read request

The following structures are searched in order:

1. Current memtable (in memory).
2. From the most recent to the least recent, the index (in-memory) is searched
   for a key range that contains the requested key.
3. Upon an index hit, the relevant SST segment block is read from disk, and the
   value corresponding to the key is returned.


## Write-Ahead Log (WAL)

### WAL actions

A WAL action is an write command performed by the database, either as part of
automatic maintenance or at the initiative of the user.

We distinguish actions taking place in the usernamespace from actions taking
place in the master namespace.

User namespace actions:

* `INSERT`: Adding a new key/value pair, or replacing the exiting value with a
  new value.
* `DELETE`: Replacing the existing value with a tombstone value.

Master namespace actions:

* `CREATE_NS`: Create a new user namespace, i.e. add a new key to the master
  SST.
* `ADD_NS_SEG`: Add a new SST segment to a namespace.
* `DELETE_NS_SEG`: Delete an SST segment from a namespace.

### WAL replay

If the WAL file for a namespace exists and is not empty upon database start,
this means that data changes may have not made their way to SST segments stored
on disk. Therefore, if the WAL exists and is not empty, we will simply apply
the commands it contains to the relevant namespaces. We do not immediately take
steps to store these changes on disk or truncate the WAL. These operations will
be taken care of when the database is closed. This approach maintains WAL
processing simplicity: the WAL is "replayed" on startup, the WAL is fed during
queries, and the WAL is truncated on shutdown.

### When is a master namespace segment created?

New SST segments are created when the memtable contains records at the time of
database shutdown. Records are added to the master memtable during several
actions:

1. A user namespace is created (WAL command is `CREATE_NS`).
2. A user namespace is closed (WAL command is `ADD_NS_SEG`).

To replay `CREATE_NS`, we put a record to the master memtable that has the
namespace name as the key, `NULL` as the value, and 0 as the value size.

To replay `ADD_SST_SEG`, we put a record to the master memtable that has the
namespace name as the key, and serialized SST segment paths (all paths to be
added) as the value. The WAL stores the full value.

### How do we log writes made to the database file?

The database file is the one that has the path used in the function `db_open`
of the `io` module. This file stores the list of SST segments for the master
table. There is a WAL for the database file as well, which has the same path as
the database file with a `.wal` suffix. Because there is no memtable for the
database file operations, restoring this WAL involves applying WAL actions
directly to disk.

Contrary to tables, which are segmented in separate files, there is a single
database file. Partial writing to this file could irremediably corrupt the
database, so we always write all master table paths to the the database WAL,
and also back to the database file. This way, the full file containing all
master table paths can be restored from the WAL.
