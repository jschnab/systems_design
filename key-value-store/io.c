#include <string.h>

#include "io.h"


#define ATTR_SIZE(Struct, Attribute) sizeof(((Struct*)0)->Attribute)

/* Segment file header offsets. */
#define VER_OFFSET 0
#define VER_SZ 8
#define NUM_REC_OFFSET (VER_OFFSET + VER_SZ)
#define NUM_REC_SZ 8
#define DATA_START_OFFSET (NUM_REC_OFFSET + NUM_REC_SZ)
#define DATA_START_SZ 8
#define INDEX_OFFSET (DATA_START_OFFSET + DATA_START_SZ)

/* Record offsets.  */
#define RECORD_LEN_SZ 4
#define KEY_LEN_SZ 1
#define KEY_MAX_LEN 256

/* Index region offsets (relative to the start of the index region). */
#define INDEX_LEN_SZ 4
#define INDEX_ITEMS_OFFSET (INDEX_OFFSET + INDEX_LEN_SZ)
#define RECORD_OFFSET_SZ 8
#define INDEX_INTERVAL 1000
#define INDEX_ITEM_CST_SZ (KEY_LEN_SZ + RECORD_OFFSET_SZ)
#define INDEX_ITEM_MAX_SZ (INDEX_ITEM_CST_SZ + KEY_MAX_LEN)


const char *VERSION = "0.1.0\0\0\0";


void index_add_item(TreeNode *node, long offset, Index *index) {
    IndexItem *item = index_item_create();
    item->key_size = node->key_size;
    item->key = (char *) malloc_safe(node->key_size + 1);
    strcpy(item->key, node->key);
    item->record_offset = offset;
    list_append(index->list, item);
    index->n++;
    index->size += INDEX_ITEM_CST_SZ + node->key_size;
}


Index *index_build(RBTree *tree) {
    Index *index = index_create();
    TreeNode *node = tree_leftmost_node(tree->root);
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
    TreeNode *node = tree_leftmost_node(tree->root);
    while (node != NIL) {
        if (node->value != NULL) {
            write_record(node, fp);
        }
        node = tree_successor_node(node);
    }
    fclose(fp);
}


void write_segment_header(RBTree *tree, FILE *fp) {
    Index *index = index_build(tree);

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

    index_destroy(index);
}
