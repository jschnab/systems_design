#ifndef __io__
#define __io__

#include <stdio.h>
#include <stdlib.h>

#include "alloc.h"
#include "linked_list.h"
#include "tree.h"


/*
   Index item structure:

   Element       | Size (bytes) | Offset (bytes)
   ---------------------------------------------
   key size      |       1      |       0
   key           |   key size   |       1
   record offset |       8      |  key size + 1


   Index item length: 1 + key size + 8

*/

typedef struct index {
    List *list; /* Linked list of index items. */
    long n;     /* Number of index items. */
    long size;  /* Total index size, in bytes. */
} Index;


typedef struct indexitem {
    char key_size;
    char *key;
    long record_offset;
} IndexItem;


Index *index_build(RBTree *);

void index_add_item(TreeNode *, long, Index *);

Index *index_create();

IndexItem *index_item_create();

void index_item_destroy(IndexItem *);

void write_record(TreeNode *, FILE *);

void write_segment_file(RBTree *, char *);

void write_segment_header(RBTree *, FILE *);

#endif
