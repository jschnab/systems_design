#include <string.h>

#include "alloc.h"
#include "index.h"
#include "io.h"


Index *index_build_from_file(FILE *fp) {
    Index *index = index_create();
    size_t data_size;
    void *data = read_index_data(fp, &data_size);
    int length;
    IndexItem *item;
    long offset = INDEX_LEN_SZ;
    memcpy(&length, data, INDEX_LEN_SZ);
    for (int i = 0; i < length; i++) {
        item = index_item_deserialize(data + offset);
        index_put_item(item, index);
        offset += item->key_size + RECORD_OFFSET_SZ;
    }
    return index;
}


Index *index_build_from_memtab(RBTree *tree) {
    Index *index = index_create();
    TreeNode *node = tree_leftmost_node(tree);
    long i;
    long offset = 0;
    IndexItem *item;
    for (i = 0; node != NIL; node = tree_successor_node(node), i++) {
        if (node->value == NULL) {
            i--;
            continue;
        }
        else if (i % INDEX_INTERVAL == 0) {
            item = index_item_from_memtab(node);
            item->record_offset = offset;
            index_put_item(item, index);
        }
        offset += RECORD_LEN_SZ + KEY_LEN_SZ + node->key_size + node->value_size;
    }
    return index;
}


/* Only attribute missing is record_offset, must be set separately. */
IndexItem *index_item_from_memtab(TreeNode *node) {
    return index_item_create(node->key_size, node->key, 0);
}


Index *index_create() {
    Index *new = (Index *) malloc_safe(sizeof(Index));
    new->list = (List *) list_create();
    new->n = 0;
    new->size = 0;
    return new;
};


void index_destroy(Index *index) {
    ListNode *head = index->list->head;
    ListNode *prev = NULL;
    while (head != NULL) {
        prev = head;
        index_item_destroy((IndexItem *)head->data);
        head->data = NULL;
        head = head->next;
        lnode_destroy(prev);
    }
    free_safe(index);
}


void index_put_item(IndexItem *item, Index *index) {
    list_append(index->list, item);
    index->n++;
    index->size += INDEX_ITEM_CST_SZ + item->key_size;
}


/* Returns offset of the index group that should be searched for key, or -1 if
 * the key sorts before the first key of the first index group. */
long index_search(char *key, Index *index) {
    ListNode *node = index->list->head;
    ListNode *prev = NULL;
    while (node != NULL && strcmp(key, ((IndexItem *)node->data)->key) >= 0) {
        prev = node;
        node = node->next;
    }
    if (prev != NULL) {
        return ((IndexItem *)prev->data)->record_offset;
    }
    return -1;
}


IndexItem *index_item_create(char key_size, char *key, long record_offset) {
    IndexItem *new = (IndexItem *) malloc_safe(sizeof(IndexItem));
    new->key_size = key_size;
    new->key = (char *) malloc_safe(key_size + 1);
    strcpy(new->key, key);
    new->record_offset = record_offset;
    return new;
}


IndexItem *index_item_deserialize(void *data) {
    char key_size;
    memcpy(&key_size, data, sizeof(char));
    char *key = (char *) malloc_safe(key_size + 1);
    memcpy(key, data + sizeof(char), key_size);
    key[(int)key_size] = '\0';
    long record_offset;
    memcpy(&record_offset, data + sizeof(char) + key_size, RECORD_OFFSET_SZ);
    IndexItem *new = index_item_create(key_size, key, record_offset);
    free_safe(key);
    return new;
}


void index_item_destroy(IndexItem *item) {
    free_safe(item->key);
    item->key = NULL;
    free_safe(item);
}
