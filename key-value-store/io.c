#include <string.h>

#include "debug.h"
#include "index.h"
#include "io.h"


static const char *VERSION = _VERSION;


/* should probably deprecate this function */
TreeNode *master_record_from_segment_set(char *ns_name, HashSet *set) {
    long value_size = 0;
    void *value;
    for (int i = 0; i < set->count; i++) {
        if ((set->items)[i] != HS_DELETED_ITEM) {
            /* +1 for null termination. */
            value_size += strlen((set->items)[i]) + 1;
        }
    }
    value = malloc_safe(value_size);
    int len;
    for (int i = 0; i < set->size; i++) {
        if ((set->items)[i] != HS_DELETED_ITEM) {
            len = strlen((set->items)[i]);
            strcpy(value, (set->items)[i]);
            ((char *)value)[len] = '\0';
            value += len + 1;
        }
    }
    return tnode_create(ns_name, value, value_size);
}


/* Consider removing data_size, it does not seem to be used by caller */
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


/* Consider refactoring this function to take a file path as input. */
RBTree *read_sst_segment(FILE *fp) {
    fseek(fp, DATA_START_OFFSET, SEEK_SET);
    long data_offset;
    fread(&data_offset, DATA_START_SZ, 1, fp);
    fseek(fp, data_offset, SEEK_SET);
    RBTree *memtab = tree_create();
    long record_size = 0;
    char key_size = 0;
    char *key = NULL;
    long value_size;
    void *value = NULL;
    size_t bytes_read = 0;
    while (true) {
        bytes_read = fread(&record_size, RECORD_LEN_SZ, 1, fp);
        if (bytes_read < 1) {
            break;
        }
        fread(&key_size, KEY_LEN_SZ, 1, fp);
        key = malloc_safe(key_size + 1);
        fread(key, key_size, 1, fp);
        key[(int)key_size] = '\0';
        value_size = record_size - RECORD_LEN_SZ - KEY_LEN_SZ - key_size;
        value = malloc_safe(value_size);
        fread(value, value_size, 1, fp);
        tree_insert(memtab, key, value, value_size);
        free_safe(key);
        free_safe(value);
    }
    return memtab;
}


void *read_sst_block(FILE *fp, long start, long end) {
    void *data = malloc_safe(end - start);
    fseek(fp, start, SEEK_SET);
    fread(data, end - start, 1, fp);
    return data;
}


/* Reads a Write-Ahead Log into an RB tree, i.e. restores memtable from WAL. */
RBTree *restore_wal(FILE *fp, unsigned long file_size) {
    unsigned long wal_data_size = file_size - VER_SZ;
    debug("wal data size: %ld bytes", wal_data_size);
    void *wal_data = malloc_safe(wal_data_size);
    long record_size = 0;
    char command = 0;
    char key_size = 0;
    char *key = NULL;
    long value_size = 0;
    void *value = NULL;
    unsigned long off = 0;
    RBTree *memtab = tree_create();
    fseek(fp, VER_SZ, SEEK_SET);
    fread(wal_data, wal_data_size, 1, fp);
    while (off < wal_data_size) {
        memcpy(&record_size, wal_data + off, RECORD_LEN_SZ);
        debug("record size: %ld", record_size);
        off += RECORD_LEN_SZ;
        memcpy(&command, wal_data + off, WAL_CMD_SZ);
        debug("command: %d", command);
        off += WAL_CMD_SZ;
        memcpy(&key_size, wal_data + off, KEY_LEN_SZ);
        debug("key size: %d", key_size);
        off += KEY_LEN_SZ;
        key = (char *) malloc_safe(key_size + 1);
        memcpy(key, wal_data + off, key_size);
        debug("key: %s", key);
        off += key_size;
        key[(int)key_size] = '\0';
        value_size = record_size - RECORD_LEN_SZ - WAL_CMD_SZ - KEY_LEN_SZ - key_size;
        debug("value size: %ld", value_size);
        value = malloc_safe(value_size);
        memcpy(value, wal_data + off, value_size);
        off += value_size;
        switch (command) {
            case INSERT:
            /* Use INSERT for both master and user tables. */
            case ADD_SST_SEG:
                tree_insert(memtab, key, value, value_size);
                break;
            case DELETE:
                tree_delete(memtab, key);
            case CREATE_NS:
                tree_insert(memtab, key, NULL, 0);
        }
        free(key);
        free(value);
    }
    free(wal_data);
    return memtab;
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
        /* We don't check if 'value' is NULL, because for the master table,
         * this indicates that a user namespace has no segments, yet (e.g. the
         * namespace was just created, but no records were added to it. */
        write_record(node, fp);
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
        data->start_offset += first_rec_offset;
        data->end_offset += first_rec_offset;
        /* write item start key info */
        fwrite(&data->start_key_size, KEY_LEN_SZ, 1, fp);
        fwrite(data->start_key, data->start_key_size, 1, fp);
        /* write item end key info */
        fwrite(&data->end_key_size, KEY_LEN_SZ, 1, fp);
        fwrite(data->end_key, data->end_key_size, 1, fp);
        /* write item record offsets */
        fwrite(&data->start_offset, RECORD_OFFSET_SZ, 1, fp);
        fwrite(&data->end_offset, RECORD_OFFSET_SZ, 1, fp);
        index_item = index_item->next;
    }

    index_destroy(index);
}

/*
   WAL item structure:

   Element        | Size (bytes)   |         Offset (bytes)
   --------------------------------------------------------
   record length  |       4        |               0
   WAL command    |       1        |               4
   key length     |       1        |               5
   key            |   key length   |               6
   value          |    variable    |         6 + key length


   Index item length: 1 + start key size + end key size + 8

*/

void write_wal_command(
    char command,
    char *key,
    void *value,
    long value_size,
    FILE *fp
) {
    char key_size = strlen(key);
    long total_size = RECORD_LEN_SZ + WAL_CMD_SZ + KEY_LEN_SZ + key_size + value_size;
    fseek(fp, 0, SEEK_END);
    fwrite(&total_size, RECORD_LEN_SZ, 1, fp);
    fwrite(&command, WAL_CMD_SZ, 1, fp);
    fwrite(&key_size, KEY_LEN_SZ, 1, fp);
    fwrite(key, key_size, 1, fp);
    if (value_size > 0) {
        fwrite(value, value_size, 1, fp);
    }
}


void write_wal_header(FILE *fp) {
    /* version number */
    fwrite(VERSION, VER_SZ, 1, fp);
}
