#ifndef __sst__
#define __sst__


#include <stdbool.h>
#include <stdint.h>

#include "index.h"
#include "tree.h"


typedef struct sstsegment {
    char *path;
    Index *index;
} SSTSegment;


void *read_sst_block(FILE *, long, long);

RBTree *read_sst_segment(FILE *);

SSTSegment *sstsegment_create(char *, bool);

long sstsegment_size(SSTSegment *);

TreeNode *sst_block_search(char *, void *, size_t);

void write_record(TreeNode *, FILE *);

void write_segment_file(RBTree *, char *);

void write_segment_header(RBTree *, FILE *);

#endif
