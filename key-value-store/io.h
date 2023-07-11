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


void *read_index_data(FILE *, size_t *);

void write_record(TreeNode *, FILE *);

void write_segment_file(RBTree *, char *);

void write_segment_header(RBTree *, FILE *);


#endif
