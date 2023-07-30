#include <string.h>

#include "alloc.h"
#include "index.h"
#include "io.h"


Index *index_build_from_file(FILE *fp) {
    Index *index = index_create();
    void *data = read_index_data(fp);
    int length;
    IndexItem *item;
    long offset = INDEX_LEN_SZ;
    memcpy(&length, data, INDEX_LEN_SZ);
    for (int i = 0; i < length; i++) {
        item = index_item_deserialize(data + offset);
        index_put_item(item, index);
        offset += item->start_key_size + item->end_key_size + INDEX_ITEM_CST_SZ;
    }
    return index;
}


Index *index_build_from_memtab(Memtable *memtab) {
    Index *index = index_create();
    if (memtab->n == 0) {
        return index;
    }

    IndexItem *item;
    Record *record = memtable_leftmost_record(memtab);
    char *start_key = record->key;
    char start_key_sz = record->key_size;
    char *end_key = record->key;
    char end_key_sz = record->key_size;
    long start_offset = 0;
    long end_offset = RECORD_LEN_SZ + KEY_LEN_SZ + record->key_size + record->value_size;
    record = memtable_successor_record(record);

    for (long i = 1; record != NIL; record = memtable_successor_record(record), i++) {
        if (record->value == NULL) {
            i--;
            continue;
        }
        if (i % INDEX_INTERVAL == 0) {
            item = index_item_create(
                start_key_sz,
                start_key,
                end_key_sz,
                end_key,
                start_offset,
                end_offset
            );
            index_put_item(item, index);
            start_key_sz = record->key_size;
            start_key = record->key;
            start_offset = end_offset;
        }
        end_offset += RECORD_LEN_SZ + KEY_LEN_SZ + record->key_size + record->value_size;
        end_key_sz = record->key_size;
        end_key = record->key;
    }

    item = index_item_create(
        start_key_sz,
        start_key,
        end_key_sz,
        end_key,
        start_offset,
        end_offset
    );
    index_put_item(item, index);
    return index;
}


Index *index_create() {
    Index *new = (Index *) malloc_safe(sizeof(Index));
    new->segment_path = NULL;
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
    index->size += INDEX_ITEM_CST_SZ + item->start_key_size + item->end_key_size;
}


/* Determines the offset of the start (inclusive) and the end (exclusive) of
 * the index group that should be searched for key. The value of start and end
 * are set to -1 if the key sorts before the first key of the first index
 * group. */
void index_search(char *key, Index *index, long *start, long *end) {
    *start = -1;
    *end = -1;
    ListNode *record = index->list->head;
    while (
        record != NULL
        && strcmp(key, ((IndexItem *)record->data)->end_key) > 0
    ) {
        record = record->next;
    }
    if (
        record != NULL
        && strcmp(key, ((IndexItem *)record->data)->start_key) >= 0
    ) {
        *start = ((IndexItem *)record->data)->start_offset;
        *end = ((IndexItem *)record->data)->end_offset;
    }
}


IndexItem *index_item_create(
    char start_key_size,
    char *start_key,
    char end_key_size,
    char *end_key,
    long start_offset,
    long end_offset
) {
    IndexItem *new = (IndexItem *) malloc_safe(sizeof(IndexItem));
    new->start_key_size = start_key_size;
    new->start_key = (char *) malloc_safe(start_key_size + 1);
    strcpy(new->start_key, start_key);
    new->end_key_size = end_key_size;
    new->end_key = (char *) malloc_safe(end_key_size + 1);
    strcpy(new->end_key, end_key);
    new->start_offset = start_offset;
    new->end_offset = end_offset;
    return new;
}


IndexItem *index_item_deserialize(void *data) {
    char start_key_size;
    memcpy(&start_key_size, data, sizeof(char));
    char *start_key = (char *) malloc_safe(start_key_size + 1);
    memcpy(start_key, data + sizeof(char), start_key_size);
    start_key[(int)start_key_size] = '\0';

    char end_key_size;
    memcpy(&end_key_size, data + sizeof(char) + start_key_size, sizeof(char));
    char *end_key = (char *) malloc_safe(end_key_size + 1);
    memcpy(end_key, data + 2 * sizeof(char) + start_key_size, end_key_size);
    end_key[(int)end_key_size] = '\0';

    long start_offset;
    memcpy(
        &start_offset,
        data + 2 * sizeof(char) + start_key_size + end_key_size,
        RECORD_OFFSET_SZ
    );

    long end_offset;
    memcpy(
        &end_offset,
        data + 2 * sizeof(char) + start_key_size + end_key_size + RECORD_OFFSET_SZ,
        RECORD_OFFSET_SZ
    );

    IndexItem *new = index_item_create(
        start_key_size,
        start_key,
        end_key_size,
        end_key,
        start_offset,
        end_offset
    );
    free_safe(start_key);
    free_safe(end_key);
    return new;
}


void index_item_destroy(IndexItem *item) {
    free_safe(item->start_key);
    item->start_key = NULL;
    free_safe(item->end_key);
    item->end_key = NULL;
    free_safe(item);
}


/* Reads the segment file region containing the index and returns it as an void
 * pointer. */
void *read_index_data(FILE *fp) {
    fseek(fp, DATA_START_OFFSET, SEEK_SET);
    long data_offset;
    fread(&data_offset, DATA_START_SZ, 1, fp);
    void *index_data = malloc_safe(data_offset - INDEX_OFFSET);
    fseek(fp, INDEX_OFFSET, SEEK_SET);
    fread(index_data, data_offset - INDEX_OFFSET, 1, fp);
    return index_data;
}
