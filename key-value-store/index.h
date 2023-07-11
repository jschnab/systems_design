#ifndef __index__
#define __index__


#include <stdint.h>
#include <stdio.h>

#include "tree.h"


typedef struct index {
    RBTree *items;
    size_t size;
} Index;


typedef struct indexvalue {
    char key_size;
    char *key;
    long record_offset;
} IndexValue;


Index *index_build(FILE *);

Index *index_create();

void index_destroy(Index *);

IndexValue *index_get_item(char *, Index *);

void index_put_item(IndexValue *, Index *);

long index_search(char *key, Index *);

IndexValue *index_value_create(char, char *, long);

IndexValue *index_value_deserialize(void *);

void index_value_destroy(IndexValue *);


#endif
