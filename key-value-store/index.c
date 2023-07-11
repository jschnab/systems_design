#include <string.h>

#include "alloc.h"
#include "index.h"
#include "io.h"


Index *index_build(FILE *fp) {
    Index *index = index_create();
    size_t data_size;
    void *data = read_index_data(fp, &data_size);
    int length;
    IndexValue *item;
    long offset = INDEX_LEN_SZ;
    memcpy(&length, data, INDEX_LEN_SZ);
    for (int i = 0; i < length; i++) {
        item = index_value_deserialize(data + offset);
        index_put_item(item, index);
        offset += item->key_size + RECORD_OFFSET_SZ;
    }
    return index;
}


Index *index_create() {
    Index *new = (Index *) malloc_safe(sizeof(Index));
    new->items = tree_create();
    new->size = 0;
    return new;
}


void index_destroy(Index *index) {
    tree_destroy(index->items);
    free_safe(index);
}


IndexValue *index_get_item(char *key, Index *index) {
    TreeNode *node = tree_search(key, index->items);
    return (IndexValue *) node->value;
}


void index_put_item(IndexValue *item, Index *index) {
    tree_insert(index->items, item->key, item, sizeof(IndexValue));
}


IndexValue *index_value_create(char key_size, char *key, long record_offset) {
    IndexValue *new = (IndexValue *) malloc_safe(sizeof(IndexValue));
    new->key_size = key_size;
    new->key = key;
    new->record_offset = record_offset;
    return new;
}


IndexValue *index_value_deserialize(void *data) {
    char key_size;
    memcpy(&key_size, data, sizeof(char));
    char *key = (char *) malloc_safe(key_size + 1);
    memcpy(key, data + sizeof(char), key_size);
    key[(int)key_size] = '\0';
    long record_offset;
    memcpy(&record_offset, data + sizeof(char) + key_size, RECORD_OFFSET_SZ);
    return index_value_create(key_size, key, record_offset);
}


void index_value_destroy(IndexValue *item) {
    free_safe(item);
}
