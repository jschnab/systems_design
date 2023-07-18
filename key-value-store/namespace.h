#ifndef __namespace__
#define __namespace__


#include <stdio.h>

#include "hashset.h"
#include "linked_list.h"
#include "sst.h"
#include "tree.h"


typedef struct namesp {
    char *name;
    RBTree *memtab;
    char *wal_path;
    FILE *wal_fp;
    List *segment_list;  /* Stores type SSTSegment. */
    HashSet *segment_set;  /* Stores segment paths. */
} Namespace;


RBTree *merge_memtables(RBTree *, RBTree *, Namespace *);

void merge_memtables_insert(TreeNode *, RBTree *, Namespace *);

void namespace_compact(Namespace *);

List *namespace_destroy(Namespace *);

Namespace *namespace_init(char *, char *, char **, long);

void namespace_insert(char, char *, void *, size_t, Namespace *);

TreeNode *namespace_search(char *, Namespace *);

char *random_string(long);

#endif
