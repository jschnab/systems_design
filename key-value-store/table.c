#include <stdlib.h>
#include <string.h>

#include "alloc.h"
#include "debug.h"
#include "io.h"
#include "table.h"

#define RANDOM_STR_LEN 20


void master_table_segments_to_root(Table *tb, FILE *root) {
    debug("master table has %ld segments", tb->segment_list->n);
    fseek(root, SEG_NUM_OFF, SEEK_SET);
    fwrite(&tb->segment_list->n, SEG_NUM_SZ, 1, root);
    if (tb->segment_list->n > 0) {
        debug("writing segments to root file");
        ListNode *record;
        for (record = tb->segment_list->head; record != NULL; record = record->next) {
            SSTSegment *seg = (SSTSegment *)record->data;
            debug("writing master SST segment path %s", seg->path);
            char path_len = strlen(seg->path);
            fwrite(&path_len, SEG_PATH_LEN_SZ, 1, root);
            fwrite(seg->path, path_len, 1, root);
        }
    }
}


/* Save the memtable as a new SST segment and append the segment path to the
 * list and set of SST segments. */
void memtable_save(Table *tb) {
    if (tb->memtab->n > 0) {
        char *segment_path = random_string(RANDOM_STR_LEN + 1);
        debug("writing memtable to %s", segment_path);
        write_segment_file(tb->memtab, segment_path);
        debug("finished writing memtable to %s", segment_path);
        debug("adding segment path %s to segment list", segment_path);
        list_append_left(tb->segment_list, sstsegment_create(segment_path, false));
        hs_add(tb->segment_set, segment_path);
    }
}

/* Merge two memtables in a new memtable and return it. If the two original
 * memtables have a record with the same key, the record from t1 is used.
 * We pass the tabke object to access the relevant WAL.
 * The algorithm is the 'merge' of merge-sort. */
Memtable* memtables_merge(Memtable *t1, Memtable *t2, Table *tb) {
    Memtable *result = memtable_create();
    Record *n1 = memtable_leftmost_record(t1);
    Record *n2 = memtable_leftmost_record(t2);
    Record *insert;  /* Points to the current record to insert. */
    int cmp = 0;
    while (n1 != NIL && n2 != NIL) {
        cmp = record_comp(n1, n2);
        if (cmp <= 0) {
            insert = n1;
            n1 = memtable_successor_record(n1);
            if (cmp == 0) {
                n2 = memtable_successor_record(n2);
            }
        }
        else {
            insert = n2;
            n2 = memtable_successor_record(n2);
        }
        memtables_merge_insert(insert, result, tb);
    }
    if (n1 != NIL) {
        while (n1 != NIL) {
            memtables_merge_insert(n1, result, tb);
            n1 = memtable_successor_record(n1);
        }
    }
    else if (n2 != NIL) {
        while (n2 != NIL) {
            memtables_merge_insert(n2, result, tb);
            n2 = memtable_successor_record(n2);
        }
    }
    return result;
}


/* Insert functionality of the function 'memtables_merge'. */
void memtables_merge_insert(Record *record, Memtable *memtab, Table *tb) {
    debug("inserting key '%s' in table '%s'", record->key, tb->name);
    write_wal_command(INSERT, record->key, record->value, record->value_size, tb->wal_fp);
    debug("wrote command '%d' to WAL", INSERT);
    memtable_insert(memtab, record->key, record->value, record->value_size);
    debug("inserted key '%s' in memtab", record->key);
}


void table_compact(Table *tb) {
    if (tb->memtab->data_size == 0) {
        return;
    }
    debug("compacting table '%s'", tb->name);
    ListNode *next_seg = tb->segment_list->head;
    SSTSegment *sst;
    if (next_seg != NULL) {
        sst = (SSTSegment *)next_seg->data;
    }
    FILE *fp;
    Memtable *next_memtab;
    Memtable *merged;
    long memtab_size = tb->memtab->data_size + tb->memtab->n * (RECORD_LEN_SZ + KEY_LEN_SZ);
    debug("current memtab size: %ld", memtab_size);
    while (next_seg != NULL && memtab_size + sstsegment_size(sst) < MAX_SEG_SZ) {
        debug("reading segment: %s", sst->path);
        fp = fopen(sst->path, "r");
        next_memtab = read_sst_segment(fp);
        fclose(fp);
        debug("merging memtable with segment %s", sst->path);
        merged = memtables_merge(tb->memtab, next_memtab, tb);
        debug("merged memtable");
        memtab_size = merged->data_size + merged->n * (RECORD_LEN_SZ + KEY_LEN_SZ);
        debug("new memtable size: %ld", memtab_size);
        free_safe(tb->memtab);
        debug("deallocated current memtable");
        tb->memtab = merged;
        free_safe(next_memtab);
        debug("deallocated current sst segment memtable");
        next_seg = next_seg->next;
        debug("removing from segment set: %s", sst->path);
        hs_discard(tb->segment_set, sst->path);
        debug("removing from segment list: %s", sst->path);
        list_delete(tb->segment_list, 0);
        debug("deleting file: %s", sst->path);
        remove(sst->path);
        debug("removed from segment list");
        if (next_seg != NULL) {
            sst = (SSTSegment *)next_seg->data;
        }
    }
    debug("finished compacting table '%s'", tb->name);
}


/* Delete the record with the specified key from a table. */
void table_delete(char cmd, char *key, Table *tb) {
    debug("deleting key '%s' from table '%s'", key, tb->name);
    write_wal_command(cmd, key, NULL, 0, tb->wal_fp);
    debug("wrote command '%d' to WAL", cmd);
    memtable_delete(tb->memtab, key);
    debug("deleted key '%s' from memtab", key);
}


/* Truncates the WAL, then destroy and cleanup the table object. */
void table_destroy(Table *tb) {
    debug("destroying table '%s'", tb->name);
    fseek(tb->wal_fp, 0, SEEK_END);
    debug("WAL %s has len %ld", tb->wal_path, ftell(tb->wal_fp));
    tb->wal_fp = truncate_wal(tb->wal_path, tb->wal_fp);
    fclose(tb->wal_fp);
    memtable_destroy(tb->memtab);
    hs_destroy(tb->segment_set);
    list_destroy(tb->segment_list);
    free_safe(tb);
}


/* Searches a key in a table (memtables, then SST segments) and returns a
 * new Record object containing the corresponding value. If the key is not
 * found, returns NULL. */
Record *table_get(char *key, Table *tb) {
    Record *found = memtable_search(key, tb->memtab);
    if (found != NULL) {
        debug("key '%s' found in memtable", key);
        return record_create(found->key, found->value, found->value_size);
    }
    debug("key '%s' not found in memtable, searching SST segments", key);
    Record *result = NULL;
    long start;
    long end;
    ListNode *record = tb->segment_list->head;
    while (record != NULL) {
        SSTSegment *segment = (SSTSegment *) record->data;
        debug("searching segment path %s", segment->path);
        index_search(key, segment->index, &start, &end);
        if (start != -1) {
            debug(
                "found candidate index block for key '%s' between offsets %ld and %ld",
                key,
                start,
                end
            );
            FILE *fp = fopen(segment->path, "r");
            void *data = read_sst_block(fp, start, end);
            result = sst_block_search(key, data, end - start);
            break;
        }
        record = record->next;
    }
    return result;
}


Table *table_init(char *name, char **segment_paths, long n_segments) {
    Table *tb = (Table *) malloc_safe(sizeof(Table));
    int len = strlen(name);
    tb->name = malloc_safe(len + 1);
    strcpy(tb->name, name);
    tb->name[len] = '\0';
    /* WAL path length is table name length +4 for '.wal' and +1 for zero-
     * termination. */
    char *wal_path = malloc_safe(len + 5);
    strcpy(wal_path, name);
    strcpy(wal_path + len, ".wal");
    wal_path[len + 4] = '\0';
    tb->wal_path = wal_path;
    FILE *wal_fp = fopen(wal_path, "a");
    tb->wal_fp = wal_fp;
    unsigned long wal_size = ftell(wal_fp);
    if (wal_size > 0) {
        debug("restoring WAL: %s", wal_path);
        freopen(wal_path, "r+", wal_fp);
        tb->memtab = restore_wal(wal_fp, wal_size);
        debug("finished restoring WAL: %s", wal_path);
        freopen(wal_path, "a", wal_fp);
    }
    else {
        tb->memtab = memtable_create();
    }
    write_wal_header(tb->wal_fp);
    tb->segment_list = list_create();
    tb->segment_set = hs_init();
    SSTSegment *seg;
    /* Remember to organize SST segments by age (more recent before least
     * recent). */
    for (long i = 0; i < n_segments; i++) {
        debug("reading SST segment #%ld: %s", i, segment_paths[i]);
        seg = sstsegment_create(segment_paths[i], true);
        list_append(tb->segment_list, seg);
        hs_add(tb->segment_set, segment_paths[i]);
    }
    return tb;
}


/* Put a record (insert or update) into a table.
 *
 * Required parameters are 'key', 'value', 'value_size', and 'target_tb'.
 * If the target table is a user table, pass a value for 'master_tb' and NULL
 * for root.
 * If the target table is the master table, pass NULL for 'master_tb' and a
 * file pointer to the root file for 'root'.
 */
void table_put(
    char *key,
    void *value,
    size_t value_size,
    Table *target_tb,
    Table *master_tb,
    FILE *root
) {
    char cmd;
    if (strcmp(target_tb->name, MASTER_TB_NAME) == 0 && !value) {
        cmd = CREATE_NS;
    }
    else {
        cmd = INSERT;
    }
    debug("inserting key '%s' in table '%s'", key, target_tb->name);
    write_wal_command(cmd, key, value, value_size, target_tb->wal_fp);
    debug("wrote command '%d' to WAL", cmd);
    if (target_tb->memtab->data_size + target_tb->memtab->n * (RECORD_LEN_SZ + KEY_LEN_SZ) > MAX_SEG_SZ) {
        memtable_save(target_tb);
        if (strcmp(target_tb->name, MASTER_TB_NAME) == 0) {
            master_table_segments_to_root(target_tb, root);
        }
        else {
            user_table_segments_to_master(target_tb, master_tb, root);
        }
        target_tb->wal_fp = truncate_wal(target_tb->wal_path, target_tb->wal_fp);
        target_tb->memtab = memtable_create();
    }
    memtable_insert(target_tb->memtab, key, value, value_size);
    debug("finished inserting key '%s' in memtab", key);
}


/* Returns a random string containing uppercase and lowercase english letters.
 * The memory necessary to store the string is allocated by the function. */
char *random_string(long len) {
    char charset[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    int key;
    char *str = NULL;
    if (len) {
        str = malloc_safe(len + 1);
        len--;
        for (long i = 0; i < len; i++) {
            key = rand() % (int) (sizeof charset - 1);
            str[i] = charset[key];
        }
    }
    str[len] = '\0';
    return str;
}


void user_table_close(Table *user_tb, Table *master_tb, FILE *root) {
    if (strcmp(master_tb->name, MASTER_TB_NAME) != 0) {
        log_err(
            "Argument #2 of `user_table_close` should be master table, "
            "got table named '%s'", master_tb->name
        );
        exit(1);
    }
    table_compact(user_tb);
    memtable_save(user_tb);
    debug("user table has %ld segments", user_tb->segment_list->n);
    user_table_segments_to_master(user_tb, master_tb, root);
    table_destroy(user_tb);
}


/* Put a record in the master table with the name of the user table as key and
 * the list of user table segments as value. */
void user_table_segments_to_master(Table *user_tb, Table *master_tb, FILE *root) {
    if (user_tb->segment_list->n == 0) {
        return;
    }
    debug("writing user table segments to master memtable");
    /* Copy user table name for later use, when adding segments paths
     * to master table. */
    char *user_tb_name = malloc_safe(strlen(user_tb->name) + 1);
    strcpy(user_tb_name, user_tb->name);

    /* The key is the table name, and the value the list of SST segment
     * paths. First the number of paths is stored in 8 bytes, then for each
     * path we store its length in 1 byte, then the path string.
     * First we get the total value size. */
    long value_size = SEG_NUM_SZ;
    ListNode *record;
    for (record = user_tb->segment_list->head; record != NULL; record = record->next) {
        value_size += strlen(((SSTSegment *)record->data)->path) + SEG_PATH_LEN_SZ;
    }
    debug("value size: %ld", value_size);
    /* Now we can copy segment paths to the value. */
    void *value = malloc_safe(value_size);
    memcpy(value, &user_tb->segment_list->n, SEG_NUM_SZ);
    long off = SEG_NUM_SZ;
    for (record = user_tb->segment_list->head; record != NULL; record = record->next) {
        SSTSegment *seg = (SSTSegment *)record->data;
        char path_len = strlen(seg->path);
        debug("segment %s has length %d", seg->path, path_len);
        memcpy(value + off, &path_len, SEG_PATH_LEN_SZ);
        off += SEG_PATH_LEN_SZ;
        memcpy(value + off, seg->path, path_len);
        off += path_len;
    }
    /* Put the user table paths in the master memtable. */
    table_put(
        user_tb_name,
        value,
        value_size,
        master_tb,
        NULL,
        root
    );
    free_safe(user_tb_name);
}
