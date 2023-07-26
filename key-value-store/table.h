#ifndef __table__
#define __table__


#include <stdio.h>

#include "hashset.h"
#include "linked_list.h"
#include "segment.h"
#include "tree.h"
#include "wal.h"


#define MASTER_TB_NAME "master"

/* Root file offsets. */
#define SEG_NUM_OFF VER_SZ
#define SEG_NUM_SZ 8
#define SEG_PATH_LEN_SZ 1


typedef struct table {
    char *name;
    RBTree *memtab;
    char *wal_path;
    FILE *wal_fp;
    List *segment_list;  /* Stores type SSTSegment. */
    HashSet *segment_set;  /* Stores segment paths. */
} Table;


void memtable_save(Table *);

RBTree *memtables_merge(RBTree *, RBTree *, Table *);

void memtables_merge_insert(TreeNode *, RBTree *, Table *);

char *random_string(long);

void table_compact(Table *);

void table_delete(char, char *, Table *);

void table_destroy(Table *);

Table *table_init(char *, char **, long);

void table_put(char, char *, void *, size_t, Table *);

TreeNode *table_get(char *, Table *);

void user_table_close(Table *, Table *);

void user_table_segments_to_master(Table *, Table *);


#endif
