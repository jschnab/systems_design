#include <string.h>

#include "alloc.h"
#include "io.h"
#include "sst.h"


/* Searches a key in a block of records read from disk. If a record is found,
 * de-serialize it as an RB tree node, else return NULL */
TreeNode *sst_block_search(char *key, void *data, size_t data_size) {
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
            value_size = record_size - RECORD_LEN_SZ - KEY_LEN_SZ - key_size;
            value = malloc_safe(value_size);
            memcpy(value, data + offset + RECORD_LEN_SZ + KEY_LEN_SZ + key_size, value_size);
            return tnode_create(key, value, value_size);
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
