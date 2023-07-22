#ifndef __namespace__
#define __namespace__


#include <stdio.h>

#include "hashset.h"
#include "linked_list.h"
#include "sst.h"
#include "tree.h"


/* Root file offsets. */
#define SEG_NUM_OFF VER_SZ
#define SEG_NUM_SZ 8
#define SEG_LST_OFF (SEG_NUM_OFF + SEG_NUM_SZ)
#define SEG_PATH_LEN_SZ 1


typedef struct namesp {
    char *name;
    RBTree *memtab;
    char *wal_path;
    FILE *wal_fp;
    List *segment_list;  /* Stores type SSTSegment. */
    HashSet *segment_set;  /* Stores segment paths. */
} Namespace;

typedef struct db {
    char *path;
    FILE *fp;
    Namespace *user_ns;
    Namespace *master_ns;
} Db;


RBTree *merge_memtables(RBTree *, RBTree *, Namespace *);

void merge_memtables_insert(TreeNode *, RBTree *, Namespace *);

void namespace_compact(Namespace *);

void namespace_delete(char, char *, Namespace *);

List *namespace_destroy(Namespace *);

Namespace *namespace_init(char *, char *, char **, long);

void namespace_insert(char, char *, void *, size_t, Namespace *);

TreeNode *namespace_search(char *, Namespace *);

char *random_string(long);

void user_namespace_close(Db *);

#endif
