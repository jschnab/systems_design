#include <string.h>

#include "io.h"


const char *VERSION = "0.1.0\0\0\0";


void index_add_item(TreeNode *node, long offset, XIndex *index) {
    IndexItem *item = index_item_create();
    item->key_size = node->key_size;
    item->key = (char *) malloc_safe(node->key_size + 1);
    strcpy(item->key, node->key);
    item->record_offset = offset;
    list_append(index->list, item);
    index->n++;
    index->size += INDEX_ITEM_CST_SZ + node->key_size;
}


XIndex *xindex_build(RBTree *tree) {
    XIndex *index = xindex_create();
    TreeNode *node = tree_leftmost_node(tree);
    long i;
    long offset = 0;
    for (i = 0; node != NIL; node = tree_successor_node(node), i++) {
        if (node->value == NULL) {
            i--;
            continue;
        }
        else if (i % INDEX_INTERVAL == 0) {
            index_add_item(node, offset, index);
        }
        offset += RECORD_LEN_SZ + KEY_LEN_SZ + node->key_size + node->value_size;
    }
    return index;
}


XIndex *xindex_create() {
    XIndex *new = (XIndex *) malloc_safe(sizeof(XIndex));
    new->list = (List *) list_create();
    new->n = 0;
    new->size = 0;
    return new;
};


void xindex_destroy(XIndex *index) {
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


IndexItem *index_item_create() {
    IndexItem *new = (IndexItem *) malloc_safe(sizeof(IndexItem));
    new->key_size = 0;
    new->key = NULL;
    new->record_offset = 0;
    return new;
}


void index_item_destroy(IndexItem *item) {
    free_safe(item->key);
    item->key = NULL;
    free_safe(item);
}


void *read_index_data(FILE *fp, size_t *data_size) {
    fseek(fp, DATA_START_OFFSET, SEEK_SET);
    long data_offset;
    fread(&data_offset, DATA_START_SZ, 1, fp);
    void *index_data = malloc_safe(data_offset - INDEX_OFFSET);
    fseek(fp, INDEX_OFFSET, SEEK_SET);
    fread(index_data, data_offset - INDEX_OFFSET, 1, fp);
    *data_size = data_offset - INDEX_OFFSET;
    return index_data;
}


void write_record(TreeNode *node, FILE *fp) {
    int total_size = RECORD_LEN_SZ + KEY_LEN_SZ + node->key_size + node->value_size;
    fwrite(&total_size, RECORD_LEN_SZ, 1, fp);
    fwrite(&node->key_size, KEY_LEN_SZ, 1, fp);
    fwrite(node->key, node->key_size, 1, fp);
    fwrite(node->value, node->value_size, 1, fp);
}


void write_segment_file(RBTree *tree, char *file_path) {
    FILE *fp = fopen(file_path, "w");
    write_segment_header(tree, fp);
    TreeNode *node = tree_leftmost_node(tree);
    while (node != NIL) {
        if (node->value != NULL) {
            write_record(node, fp);
        }
        node = tree_successor_node(node);
    }
    fclose(fp);
}


/* need to refactor: index_build */
void write_segment_header(RBTree *tree, FILE *fp) {
    XIndex *index = xindex_build(tree);

    /* version number */
    fwrite(VERSION, VER_SZ, 1, fp);

    /* number of records */
    fwrite(&tree->n, NUM_REC_SZ, 1, fp);

    /* 1st record offset */
    long first_rec_offset = INDEX_ITEMS_OFFSET + index->size;
    fwrite(&first_rec_offset, RECORD_OFFSET_SZ, 1, fp);

    /* index length */
    fwrite(&index->n, INDEX_LEN_SZ, 1, fp);
    /* index items */
    ListNode *index_item = index->list->head;
    IndexItem *data;
    for (int i = 0; i < index->n; i++) {
        data = (IndexItem *) index_item->data;
        data->record_offset += first_rec_offset;
        /* write item key length */
        fwrite(&data->key_size, KEY_LEN_SZ, 1, fp);
        /* write item key */
        fwrite(data->key, data->key_size, 1, fp);
        /* write item record offset */
        fwrite(&data->record_offset, RECORD_OFFSET_SZ, 1, fp);
        index_item = index_item->next;
    }

    xindex_destroy(index);
}
