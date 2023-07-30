#ifndef __sst__
#define __sst__


#include <stdbool.h>
#include <stdint.h>

#include "index.h"
#include "memtab.h"


typedef struct sstsegment {
    char *path;
    Index *index;
} SSTSegment;


void *read_sst_block(FILE *, long, long);

Memtable *read_sst_segment(FILE *);

SSTSegment *sstsegment_create(char *, bool);

long sstsegment_size(SSTSegment *);

Record *sst_block_search(char *, void *, size_t);

void write_record(Record *, FILE *);

void write_segment_file(Memtable *, char *);

void write_segment_header(Memtable *, FILE *);

#endif
