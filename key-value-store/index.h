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

   Element        | Size (bytes)   |         Offset (bytes)
   --------------------------------------------------------------------
   start key size |       1        |               0
   start key      | start key size |               1
   end key size   |       1        |       1 + start key size
   end key        |  end key size  |       2 + start key size
   start offset   |       8        | 2 + start key size + end key size
   end offset     |       8        | 10 + start key size + end key size


   Index item length: 1 + start key size + end key size + 8

*/
typedef struct indexitem {
    char start_key_size;
    char *start_key;
    char end_key_size;
    char *end_key;
    long start_offset;
    long end_offset;
} IndexItem;


Index *index_build_from_file(FILE *);

Index *index_build_from_memtab(RBTree *);

IndexItem *index_item_from_memtab(TreeNode *);

Index *index_create();

void index_destroy(Index *);

void index_put_item(IndexItem *, Index *);

void index_search(char *, Index *, long *, long *);

IndexItem *index_item_create(char, char *, char, char *, long, long);

IndexItem *index_item_deserialize(void *);

void index_item_destroy(IndexItem *);


#endif
