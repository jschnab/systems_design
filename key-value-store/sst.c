#include <string.h>

#include "alloc.h"
#include "debug.h"
#include "io.h"
#include "sst.h"


/* Searches a key in a block of records read from disk. If a record is found,
 * de-serialize it as an RB tree node, else return NULL */
TreeNode *sst_block_search(char *key, void *data, size_t data_size) {
    debug("searching SST block for key: %s", key);
    int record_size = 0;
    char key_size = 0;
    char candidate_key[KEY_MAX_LEN] = {0};
    void *value = NULL;
    long value_size = 0;
    size_t offset = 0;
    while (offset < data_size) {
        memcpy(&record_size, data + offset, RECORD_LEN_SZ);
        memcpy(&key_size, data + offset + RECORD_LEN_SZ, KEY_LEN_SZ);
        memcpy(candidate_key, data + offset + RECORD_LEN_SZ + KEY_LEN_SZ, key_size);
        candidate_key[(int)key_size] = '\0';
        if (strcmp(candidate_key, key) == 0) {
            debug("found key: %s", key);
            value_size = record_size - RECORD_LEN_SZ - KEY_LEN_SZ - key_size;
            debug("value size: %ld", value_size);
            if (value_size > 0) {
                value = malloc_safe(value_size);
                memcpy(value, data + offset + RECORD_LEN_SZ + KEY_LEN_SZ + key_size, value_size);
            }
            /* Should probably have a function 'tnode_init' that creates an
             * empty object and fill it with value obtained here, too many
             * malloc and free otherwise. */
            TreeNode *ret = tnode_init();
            ret->key = key;
            ret->key_size = key_size;
            ret->value = value;
            ret->value_size = value_size;
            return ret;
        }
        offset += record_size;
    }
    return NULL;
}



SSTSegment *sstsegment_create(char *segment_path, bool build_index) {
    SSTSegment *new = (SSTSegment *) malloc_safe(sizeof(SSTSegment));
    new->path = segment_path;
    FILE *seg = fopen(segment_path, "r");
    new->index = NULL;
    if (build_index) {
        new->index = index_build_from_file(seg);
    }
    fclose(seg);
    return new;
}
