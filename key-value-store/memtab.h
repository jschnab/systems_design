#ifndef __memtab__
#define __memtab__

#include <stdbool.h>
#include <stdlib.h>

#define RED true
#define BLACK false

#define NOFLAGS 0
#define DELETED 1


typedef struct record {
    char *key;
    void *value;
    char flags;
    char key_size;
    size_t value_size;
    struct record *parent;
    struct record *left;
    struct record *right;
    bool color;
} Record;


typedef struct memtable {
    Record *root;
    size_t n;
    size_t data_size;
} Memtable;


Record _NIL;
Record *NIL;


int record_comp(Record *, Record *);

Record *record_create(char *, void *, size_t);

void record_destroy(Record *);

Record *record_init();

void record_insert_fixup(Memtable *, Record *);

Record *record_leftmost(Record *);

void record_print(Record *);

void record_rotate_left(Memtable *, Record *);

void record_rotate_right(Memtable *, Record *);

Memtable *memtable_create();

void memtable_delete(Memtable *, char *);

void memtable_destroy(Memtable *);

void memtable_destroy_helper(Record *);

void memtable_insert(Memtable *, char *, void *, size_t, char);

Record *memtable_leftmost_record(Memtable *);

Record *memtable_search(char *, Memtable *);

Record *memtable_successor_record(Record *);

void memtable_traverse_inorder(Record *);

#endif
