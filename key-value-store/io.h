#ifndef __io__
#define __io__

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "alloc.h"
#include "linked_list.h"
#include "tree.h"


#define ATTR_SIZE(Struct, Attribute) sizeof(((Struct*)0)->Attribute)

/* Segment file header offsets. */
#define VER_OFFSET 0
#define VER_SZ 8
#define NUM_REC_OFFSET (VER_OFFSET + VER_SZ)
#define NUM_REC_SZ 8
#define DATA_START_OFFSET (NUM_REC_OFFSET + NUM_REC_SZ)
#define DATA_START_SZ 8
#define INDEX_OFFSET (DATA_START_OFFSET + DATA_START_SZ)

/* Record offsets.  */
#define RECORD_LEN_SZ 4
#define KEY_LEN_SZ 1
#define KEY_MAX_LEN 256

/* Index region offsets (relative to the start of the index region). */
#define INDEX_LEN_SZ 4
#define INDEX_ITEMS_OFFSET (INDEX_OFFSET + INDEX_LEN_SZ)
#define RECORD_OFFSET_SZ 8
#define INDEX_INTERVAL 1000
#define INDEX_ITEM_CST_SZ (KEY_LEN_SZ + RECORD_OFFSET_SZ)
#define INDEX_ITEM_MAX_SZ (INDEX_ITEM_CST_SZ + KEY_MAX_LEN)


/* XIndex is a used temporarily to write the index to disk */
typedef struct xindex {
    List *list; /* Linked list of index items. */
    long n;     /* Number of index items. */
    long size;  /* Total index size, in bytes. */
} XIndex;


/*
   Index item structure:

   Element       | Size (bytes) | Offset (bytes)
   ---------------------------------------------
   key size      |       1      |       0
   key           |   key size   |       1
   record offset |       8      |  key size + 1


   Index item length: 1 + key size + 8

*/
typedef struct indexitem {
    char key_size;
    char *key;
    long record_offset;
} IndexItem;


XIndex *xindex_build(RBTree *);

void index_add_item(TreeNode *, long, XIndex *);

XIndex *xindex_create();

void xindex_destroy(XIndex *);

IndexItem *index_item_create();

void index_item_destroy(IndexItem *);

void * read_index_data(FILE *, size_t *);

void write_record(TreeNode *, FILE *);

void write_segment_file(RBTree *, char *);

void write_segment_header(RBTree *, FILE *);


#endif
