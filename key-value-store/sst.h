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


SSTSegment *sstsegment_create(char *, bool);

long sstsegment_size(SSTSegment *);

TreeNode *sst_block_search(char *, void *, size_t);


#endif
