#include <stdlib.h>
#include <string.h>

#include "alloc.h"
#include "debug.h"
#include "io.h"
#include "table.h"
#include "tree.h"

#define RANDOM_STR_LEN 20


/* Merge two memtables in a new memtable and return it. If the two original
 * memtables have a node with the same key, the node from t1 is used.
 * We pass the tabke object to access the relevant WAL.
 * The algorithm is the 'merge' of merge-sort. */
RBTree* merge_memtables(RBTree *t1, RBTree *t2, Table *tb) {
    RBTree *result = tree_create();
    TreeNode *n1 = tree_leftmost_node(t1);
    TreeNode *n2 = tree_leftmost_node(t2);
    TreeNode *insert;  /* Points to the current node to insert. */
    int cmp = 0;
    while (n1 != NIL && n2 != NIL) {
        cmp = tnode_comp(n1, n2);
        if (cmp <= 0) {
            insert = n1;
            n1 = tree_successor_node(n1);
            if (cmp == 0) {
                n2 = tree_successor_node(n2);
            }
        }
        else {
            insert = n2;
            n2 = tree_successor_node(n2);
        }
        merge_memtables_insert(insert, result, tb);
    }
    if (n1 != NIL) {
        while (n1 != NIL) {
            merge_memtables_insert(n1, result, tb);
            n1 = tree_successor_node(n1);
        }
    }
    else if (n2 != NIL) {
        while (n2 != NIL) {
            merge_memtables_insert(n2, result, tb);
            n2 = tree_successor_node(n2);
        }
    }
    return result;
}


/* Insert functionality of the function 'merge_memtables'. */
void merge_memtables_insert(TreeNode *node, RBTree *tree, Table *tb) {
    debug("inserting key '%s' in table '%s'", node->key, tb->name);
    char cmd;
    if (strcmp(tb->name, MASTER_TB_NAME) == 0) {
        /* User INSERT */
        cmd = ADD_SST_SEG;
    }
    else {
        cmd = INSERT;
    }
    write_wal_command(cmd, node->key, node->value, node->value_size, tb->wal_fp);
    debug("wrote command '%d' to WAL", INSERT);
    tree_insert(tree, node->key, node->value, node->value_size);
    debug("inserted key '%s' in memtab", node->key);
}


void table_compact(Table *tb) {
    debug("compacting table '%s'", tb->name);
    ListNode *next_seg = tb->segment_list->head;
    SSTSegment *sst;
    if (next_seg != NULL) {
        sst = (SSTSegment *)next_seg->data;
    }
    FILE *fp;
    RBTree *next_memtab;
    RBTree *merged;
    long memtab_size = tb->memtab->data_size + tb->memtab->n * (RECORD_LEN_SZ + KEY_LEN_SZ);
    debug("current memtab size: %ld", memtab_size);
    while (next_seg != NULL && memtab_size + sstsegment_size(sst) < MAX_SEG_SIZE) {
        debug("reading segment: %s", sst->path);
        fp = fopen(sst->path, "r");
        next_memtab = read_sst_segment(fp);
        fclose(fp);
        debug("merging memtable with segment %s", sst->path);
        merged = merge_memtables(tb->memtab, next_memtab, tb);
        debug("merged memtable");
        memtab_size = merged->data_size + tb->memtab->n * (RECORD_LEN_SZ + KEY_LEN_SZ);
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
        debug("removed from segment list");
        if (next_seg != NULL) {
            sst = (SSTSegment *)next_seg->data;
        }
        debug("deleting file: %s", sst->path);
        remove(sst->path);
    }
    debug("finished compacting table '%s'", tb->name);
}


/* Writes the memtable to disk, truncates the WAL, and writes the path of the
 * new SST segment in the table segment list.
 * We return the segment list so that the caller can take steps to save the
 * segment paths:
 * - user SST segment paths are written to master SST
 * - master SST segment paths are written to root file
 *
 * The return value must be freed by caller.
 *
 * We should refactor this function to truncate the WAL after SST segment paths
 * have been written to the higher level WAL (e.g. master WAL in the case of a
 * user table. Otherwise, we won't know at which path SST segment path are
 * located. */
List *table_destroy(Table *tb) {
    debug("destroying table '%s'", tb->name);
    debug("memtab has %ld items", tb->memtab->n);
    if (tb->memtab->n > 0) {
        char *segment_path = random_string(RANDOM_STR_LEN + 1);
        debug("writing memtable to %s", segment_path);
        write_segment_file(tb->memtab, segment_path);
        debug("adding segment path %s to segment list", segment_path);
        list_append_left(tb->segment_list, sstsegment_create(segment_path, false));
    }
    tree_destroy(tb->memtab);
    fseek(tb->wal_fp, 0, SEEK_END);
    debug("WAL %s has len %ld", tb->wal_path, ftell(tb->wal_fp));
    debug("truncating WAL: %s", tb->wal_path);
    FILE *fp = freopen(tb->wal_path, "w", tb->wal_fp);
    if (fp == NULL) {
        log_warn("failed to truncated WAL %s", tb->wal_path);
    }
    fclose(tb->wal_fp);
    hs_destroy(tb->segment_set);
    List *ret = tb->segment_list;
    free_safe(tb);
    return ret;
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
        tb->memtab = tree_create();
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


void table_put(char cmd, char *key, void *value, size_t value_size, Table *tb) {
    debug("inserting key '%s' in table '%s'", key, tb->name);
    write_wal_command(cmd, key, value, value_size, tb->wal_fp);
    debug("wrote command '%d' to WAL", cmd);
    tree_insert(tb->memtab, key, value, value_size);
    debug("inserted key '%s' in memtab", key);
}


/* Delete the record with the specified key from a table. */
void table_delete(char cmd, char *key, Table *tb) {
    debug("deleting key '%s' from table '%s'", key, tb->name);
    write_wal_command(cmd, key, NULL, 0, tb->wal_fp);
    debug("wrote command '%d' to WAL", cmd);
    tree_delete(tb->memtab, key);
    debug("deleted key '%s' from memtab", key);
}


/* Searches a key in a table (memtables, then SST segments) and returns a
 * new TreeNode object containing the corresponding value. If the key is not
 * found, returns NULL. */
TreeNode *table_get(char *key, Table *tb) {
    TreeNode *found = tree_search(key, tb->memtab);
    if (found != NULL) {
        debug("key '%s' found in memtable", key);
        return tnode_create(found->key, found->value, found->value_size);
    }
    debug("key '%s' not found in memtable, searching SST segments", key);
    TreeNode *result = NULL;
    long start;
    long end;
    ListNode *node = tb->segment_list->head;
    while (node != NULL) {
        SSTSegment *segment = (SSTSegment *) node->data;
        debug("searching segment path %s", segment->path);
        index_search(key, segment->index, &start, &end);
        if (start != -1) {
            debug("found key '%s' between offsets %ld and %ld", key, start, end);
            FILE *fp = fopen(segment->path, "r");
            void *data = read_sst_block(fp, start, end);
            result = sst_block_search(key, data, end - start);
            break;
        }
        node = node->next;
    }
    return result;
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


void user_table_close(Table *user_tb, Table *master_tb) {
    if (strcmp(master_tb->name, MASTER_TB_NAME) != 0) {
        log_err(
            "Argument #2 of `user_table_close` should be master table, "
            "got table named '%s'", master_tb->name
        );
        exit(1);
    }
    /* Copy user table name for later use, when adding segments paths
     * to master table. */
    char *user_tb_name = malloc_safe(strlen(user_tb->name) + 1);
    strcpy(user_tb_name, user_tb->name);
    table_compact(user_tb);
    List *segments = table_destroy(user_tb);
    debug("user table has %ld segments", segments->n);
    if (segments->n > 0) {
        debug("writing segments to master SST memtable");
        /* The key is the table name, and the value the list of SST segment
         * paths. First the number of paths is stored in 8 bytes, then for each
         * path we store its length in 1 byte, then the path string.
         * First we get the total value size. */
        long value_size = SEG_NUM_SZ;
        for (ListNode *node = segments->head; node != NULL; node = node->next) {
            value_size += strlen(((SSTSegment *)node->data)->path) + SEG_PATH_LEN_SZ;
        }
        debug("value size: %ld", value_size);
        /* Now we can copy segment paths to the value. */
        void *value = malloc_safe(value_size);
        long segment_count = (long) segments->n;
        memcpy(value, &segment_count, SEG_NUM_SZ);
        long off = SEG_NUM_SZ;
        for (ListNode *node= segments->head; node != NULL; node = node->next) {
            SSTSegment *seg = (SSTSegment *)node->data;
            char path_len = strlen(seg->path);
            debug("segment %s has length %d", seg->path, path_len);
            memcpy(value + off, &path_len, SEG_PATH_LEN_SZ);
            off += SEG_PATH_LEN_SZ;
            memcpy(value + off, seg->path, path_len);
            off += path_len;
        }
        /* Put the user table paths in the master memtable. */
        table_put(
            /* Use INSERT */
            ADD_SST_SEG,
            user_tb_name,
            value,
            value_size,
            master_tb
        );
        free_safe(user_tb_name);
    }
    list_destroy(segments);
}
