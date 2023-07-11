#include <string.h>

#include "index.h"
#include "io.h"


const char *VERSION = "0.1.0\0\0\0";


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


void write_segment_header(RBTree *tree, FILE *fp) {
    Index *index = index_build_from_memtab(tree);

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
