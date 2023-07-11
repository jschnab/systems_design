#ifndef __index__
#define __index__


#include <stdint.h>
#include <stdio.h>

#include "linked_list.h"
#include "tree.h"


/* XIndex is a used temporarily to write the index to disk */
typedef struct index {
    List *list; /* Linked list of index items. */
    long n;     /* Number of index items. */
    long size;  /* Total index size, in bytes. */
} Index;


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


Index *index_build_from_file(FILE *);

Index *index_build_from_memtab(RBTree *);

IndexItem *index_item_from_memtab(TreeNode *);

Index *index_create();

void index_destroy(Index *);

void index_put_item(IndexItem *, Index *);

long index_search(char *, Index *);

IndexItem *index_item_create(char, char *, long);

IndexItem *index_item_deserialize(void *);

void index_item_destroy(IndexItem *);


#endif
