#ifndef __io__
#define __io__

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "alloc.h"
#include "linked_list.h"
#include "hashset.h"
#include "tree.h"


#define ATTR_SIZE(Struct, Attribute) sizeof(((Struct*)0)->Attribute)

#define _VERSION "0.1.0\0\0\0"

/* Interface command codes for user table WAL. */
#define INSERT 1
#define DELETE 2
/* Interface command codes for master table WAL. */ 
#define CREATE_NS 3
#define ADD_SST_SEG 4 // Use INSERT instead of ADD_SST_SEG
#define DELETE_SST_SEG 5

/* Segment file header offsets. */
#define VER_OFFSET 0
#define VER_SZ 8
#define NUM_REC_OFFSET (VER_OFFSET + VER_SZ)
#define NUM_REC_SZ 8
#define DATA_START_OFFSET (NUM_REC_OFFSET + NUM_REC_SZ)
#define DATA_START_SZ 8
#define INDEX_OFFSET (DATA_START_OFFSET + DATA_START_SZ)

#define MAX_SEG_SIZE 1000000

/* Record offsets.  */
#define RECORD_LEN_SZ 4
#define KEY_LEN_SZ 1
#define KEY_MAX_LEN 256
#define RECORD_CST_SZ (RECORD_LEN_SZ + KEY_LEN_SZ)

/* Index region offsets (relative to the start of the index region). */
#define INDEX_LEN_SZ 4
#define INDEX_ITEMS_OFFSET (INDEX_OFFSET + INDEX_LEN_SZ)
#define RECORD_OFFSET_SZ 8
#define INDEX_INTERVAL 2
#define INDEX_ITEM_CST_SZ (2 * (KEY_LEN_SZ + RECORD_OFFSET_SZ))
#define INDEX_ITEM_MAX_SZ (INDEX_ITEM_CST_SZ + 2 * KEY_MAX_LEN)

/* Write-Ahead Log offsets and sizes. */
#define WAL_CMD_SZ 1

#define MASTER_NS_NAME "master"
#define MASTER_WAL_PATH "master.wal"


TreeNode *master_record_from_segment_set(char *, HashSet *);

void *read_index_data(FILE *, size_t *);

RBTree *read_sst_segment(FILE *);

void *read_sst_block(FILE *, long, long);

RBTree *restore_wal(FILE *, unsigned long);

void write_record(TreeNode *, FILE *);

void write_segment_file(RBTree *, char *);

void write_segment_header(RBTree *, FILE *);

void write_wal_command(char, char *, void *, long, FILE *);

void write_wal_header(FILE *);


#endif
