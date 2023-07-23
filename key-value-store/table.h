#ifndef __table__
#define __table__


#include <stdio.h>

#include "hashset.h"
#include "linked_list.h"
#include "sst.h"
#include "tree.h"


#define MASTER_TB_NAME "master"

/* Root file offsets. */
#define SEG_NUM_OFF VER_SZ
#define SEG_NUM_SZ 8
#define SEG_LST_OFF (SEG_NUM_OFF + SEG_NUM_SZ)
#define SEG_PATH_LEN_SZ 1


typedef struct table {
    char *name;
    RBTree *memtab;
    char *wal_path;
    FILE *wal_fp;
    List *segment_list;  /* Stores type SSTSegment. */
    HashSet *segment_set;  /* Stores segment paths. */
} Table;


RBTree *merge_memtables(RBTree *, RBTree *, Table *);

void merge_memtables_insert(TreeNode *, RBTree *, Table *);

void table_compact(Table *);

void table_delete(char, char *, Table *);

List *table_destroy(Table *);

Table *table_init(char *, char **, long);

void table_put(char, char *, void *, size_t, Table *);

TreeNode *table_get(char *, Table *);

char *random_string(long);

void user_table_close(Table *, Table *);

#endif
