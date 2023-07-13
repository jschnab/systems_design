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


char *random_string(long);

HashSet *namespace_destroy(Namespace *);

Namespace *namespace_init(char *, char *, char **, long);

void namespace_insert(char, char *, void *, size_t, Namespace *);

void namespace_search(char *, Namespace *);

#endif
