#include <string.h>

#include "alloc.h"
#include "debug.h"
#include "io.h"
#include "segment.h"


static const char *VERSION = _VERSION;


/* Reads data from a segment file between the offsets 'start' and 'end', then
 * returns it as a void pointer. */
void *read_sst_block(FILE *fp, long start, long end) {
    void *data = malloc_safe(end - start);
    fseek(fp, start, SEEK_SET);
    fread(data, end - start, 1, fp);
    return data;
}


/* Reads the segment file region that contains records, serializes it as a
 * memtable, and returns the memtable.
 * Consider refactoring this function to take a file path as input.
 * Consider putting record deserialization in its own function. */
Memtable *read_sst_segment(FILE *fp) {
    fseek(fp, DATA_START_OFFSET, SEEK_SET);
    long data_offset;
    fread(&data_offset, DATA_START_SZ, 1, fp);
    fseek(fp, data_offset, SEEK_SET);
    Memtable *memtab = memtable_create();
    long record_size = 0;
    char key_size = 0;
    char key[KEY_MAX_LEN] = {0};
    char flags = NOFLAGS;
    long value_size;
    void *value = NULL;
    size_t bytes_read = 0;
    while (true) {
        bytes_read = fread(&record_size, RECORD_LEN_SZ, 1, fp);
        if (bytes_read < 1) {
            break;
        }
        fread(&key_size, KEY_LEN_SZ, 1, fp);
        fread(key, key_size, 1, fp);
        key[(int)key_size] = '\0';
        fread(&flags, RECORD_FLAGS_SZ, 1, fp);
        value_size = record_size - RECORD_CST_SZ - key_size;
        value = malloc_safe(value_size);
        fread(value, value_size, 1, fp);
        memtable_insert(memtab, key, value, value_size, flags);
        free_safe(value);
    }
    return memtab;
}


/* Searches a key in a block of records read from disk. If a record is found,
 * de-serialize it as a new record, else return NULL */
Record *sst_block_search(char *key, void *data, size_t data_size) {
    debug("searching SST block for key: %s", key);
    int record_size = 0;
    char key_size = 0;
    char candidate_key[KEY_MAX_LEN] = {0};
    char flags = NOFLAGS;
    void *value = NULL;
    long value_size = 0;
    size_t offset = 0;
    while (offset < data_size) {
        memcpy(&record_size, data + offset, RECORD_LEN_SZ);
        memcpy(&key_size, data + offset + RECORD_LEN_SZ, KEY_LEN_SZ);
        memcpy(candidate_key, data + offset + RECORD_LEN_SZ + KEY_LEN_SZ, key_size);
        candidate_key[(int)key_size] = '\0';
        memcpy(&flags, data + offset + RECORD_LEN_SZ + KEY_LEN_SZ + key_size, RECORD_FLAGS_SZ);
        if (strcmp(candidate_key, key) == 0) {
            debug("found key: %s", key);
            value_size = record_size - RECORD_CST_SZ - key_size;
            if (value_size > 0) {
                value = malloc_safe(value_size);
                memcpy(value, data + offset + RECORD_CST_SZ + key_size, value_size);
            }
            Record *ret = record_init();
            ret->key = key;
            ret->key_size = key_size;
            ret->value = value;
            ret->value_size = value_size;
            ret->flags = flags;
            return ret;
        }
        offset += record_size;
    }
    return NULL;
}


/* Returns the size of a segment's data (excluding the header), in bytes. */
long sstsegment_size(SSTSegment *segment) {
    debug("calculating size of sst segment %s", segment->path);
    FILE *fp = fopen(segment->path, "r");
    if (!fp) {
        log_err("could not open %s, exiting", segment->path);
        exit(1);
    }
    long data_off;
    fseek(fp, DATA_START_OFFSET, SEEK_SET);
    fread(&data_off, DATA_START_SZ, 1, fp);
    debug("read data offset: %ld", data_off);
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp) - data_off;
    debug("read file size: %ld", size);
    fclose(fp);
    return size;
}


SSTSegment *sstsegment_create(char *segment_path, bool build_index) {
    SSTSegment *new = (SSTSegment *) malloc_safe(sizeof(SSTSegment));
    new->path = segment_path;
    new->index = NULL;
    if (build_index) {
        FILE *seg = fopen(segment_path, "r");
        if (seg == NULL) {
            log_err("could not open file '%s'", segment_path);
            exit(1);
        }
        new->index = index_build_from_file(seg);
        fclose(seg);
    }
    return new;
}


/* Writes a single memtable record to a segment file. */
void write_record(Record *record, FILE *fp) {
    int total_size = RECORD_CST_SZ + record->key_size + record->value_size;
    fwrite(&total_size, RECORD_LEN_SZ, 1, fp);
    fwrite(&record->key_size, KEY_LEN_SZ, 1, fp);
    fwrite(record->key, record->key_size, 1, fp);
    fwrite(&record->flags, RECORD_FLAGS_SZ, 1, fp);
    fwrite(record->value, record->value_size, 1, fp);
}


/* Writes the whole memtable to a segment file. */
void write_segment_file(Memtable *memtab, char *file_path) {
    FILE *fp = fopen(file_path, "w");
    write_segment_header(memtab, fp);
    Record *record = memtable_leftmost_record(memtab);
    while (record != NIL) {
        /* We don't check if 'value' is NULL, because for the master table,
         * this indicates that a user table has no segments, yet (e.g. the
         * table was just created, but no records were added to it). */
        write_record(record, fp);
        record = memtable_successor_record(record);
    }
    fclose(fp);
}


/* Writes the segment header, i.e. everything that is not records: version,
 * number of records, 1st record offset, then index. */
void write_segment_header(Memtable *memtab, FILE *fp) {
    Index *index = index_build_from_memtab(memtab);

    /* version number */
    fwrite(VERSION, VER_SZ, 1, fp);

    /* number of records */
    fwrite(&memtab->n, NUM_REC_SZ, 1, fp);

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
