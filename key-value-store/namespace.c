#include <stdlib.h>
#include <string.h>

#include "alloc.h"
#include "debug.h"
#include "io.h"
#include "namespace.h"
#include "tree.h"

#define RANDOM_STR_LEN 20


/* Merge two memtables in a new memtable and return it. If the two original
 * memtables have a node with the same key, the node from t1 is used.
 * We pass the namespace object to access the relevant WAL.
 * The algorithm is the 'merge' of merge-sort. */
RBTree* merge_memtables(RBTree *t1, RBTree *t2, Namespace *ns) {
    RBTree *result = tree_create();
    TreeNode *n1 = tree_leftmost_node(t1);
    TreeNode *n2 = tree_leftmost_node(t2);
    TreeNode *insert;  /* Points to the current node to insert. */
    while (n1 != NIL && n2 != NIL) {
        if (tnode_comp(n1, n2) <= 0) {
            insert = n1;
            n1 = tree_successor_node(n1);
        }
        else {
            debug("inserting sst value for key '%s'", n2->key);
            insert = n2;
            n2 = tree_successor_node(n2);
        }
        merge_memtables_insert(insert, result, ns);
    }
    if (n1 != NIL) {
        while (n1 != NIL) {
            merge_memtables_insert(n1, result, ns);
            n1 = tree_successor_node(n1);
        }
    }
    else if (n2 != NIL) {
        while (n2 != NIL) {
            merge_memtables_insert(n2, result, ns);
            n2 = tree_successor_node(n2);
        }
    }
    return result;
}


/* Insert functionality of the function 'merge_memtables'. */
void merge_memtables_insert(TreeNode *node, RBTree *tree, Namespace *ns) {
    debug("inserting key '%s' in namespace '%s'", node->key, ns->name);
    char cmd;
    if (strcmp(ns->name, MASTER_NS_NAME) == 0) {
        cmd = ADD_SST_SEG;
    }
    else {
        cmd = INSERT;
    }
    write_wal_command(cmd, node->key, node->value, node->value_size, ns->wal_fp);
    debug("wrote command '%d' to WAL", INSERT);
    tree_insert(tree, node->key, node->value, node->value_size);
    debug("inserted key '%s' in memtab", node->key);
}


void namespace_compact(Namespace *ns) {
    debug("compacting namespace '%s'", ns->name);
    ListNode *next_seg = ns->segment_list->head;
    SSTSegment *sst;
    if (next_seg != NULL) {
        sst = (SSTSegment *)next_seg->data;
    }
    FILE *fp;
    RBTree *next_memtab;
    RBTree *merged;
    long memtab_size = ns->memtab->data_size + ns->memtab->n * (RECORD_LEN_SZ + KEY_LEN_SZ);
    debug("current memtab size: %ld", memtab_size);
    while (next_seg != NULL && memtab_size + sstsegment_size(sst) < MAX_SEG_SIZE) {
        debug("reading segment: %s", sst->path);
        fp = fopen(sst->path, "r");
        next_memtab = read_sst_segment(fp);
        fclose(fp);
        debug("merging memtable with segment %s", sst->path);
        merged = merge_memtables(ns->memtab, next_memtab, ns);
        debug("merged memtable");
        memtab_size = merged->data_size + ns->memtab->n * (RECORD_LEN_SZ + KEY_LEN_SZ);
        debug("new memtable size: %ld", memtab_size);
        free_safe(ns->memtab);
        debug("deallocated current memtable");
        ns->memtab = merged;
        free_safe(next_memtab);
        debug("deallocated current sst segment memtable");
        next_seg = next_seg->next;
        debug("removing from segment set: %s", sst->path);
        hs_discard(ns->segment_set, sst->path);
        debug("removing from segment list: %s", sst->path);
        list_delete(ns->segment_list, 0);
        debug("removed from segment list");
        if (next_seg != NULL) {
            sst = (SSTSegment *)next_seg->data;
        }
        debug("deleting file: %s", sst->path);
        remove(sst->path);
    }
    debug("finished compacting namespace '%s'", ns->name);
}


/* Writes the memtable to disk, truncates the WAL, and writes the path of the
 * new SST segment in the appropriate segment list of the Db object.
 * We return the segment list so that the caller can take steps to save the
 * segment paths:
 * - user SST segment paths are written to master SST
 * - master SST segment paths are written to root file
 *
 * The return value must be freed by caller.
 *
 * We should refactor this function to truncate the WAL after SST segment paths
 * have been written to the higher level WAL (e.g. master WAL in the case of a
 * user namespace. Otherwise, we won't know at which path SST segment path are
 * located. */
List *namespace_destroy(Namespace *ns) {
    debug("destroying namespace '%s'", ns->name);
    debug("memtab has %ld items", ns->memtab->n);
    if (ns->memtab->n > 0) {
        char *segment_path = random_string(RANDOM_STR_LEN + 1);
        debug("writing memtable to %s", segment_path);
        write_segment_file(ns->memtab, segment_path);
        debug("adding segment path %s to segment list", segment_path);
        list_append_left(ns->segment_list, sstsegment_create(segment_path, false));
    }
    tree_destroy(ns->memtab);
    fseek(ns->wal_fp, 0, SEEK_END);
    debug("WAL %s has len %ld", ns->wal_path, ftell(ns->wal_fp));
    debug("truncating WAL: %s", ns->wal_path);
    FILE *fp = freopen(ns->wal_path, "w", ns->wal_fp);
    if (fp == NULL) {
        log_warn("failed to truncated WAL %s", ns->wal_path);
    }
    fclose(ns->wal_fp);
    hs_destroy(ns->segment_set);
    List *ret = ns->segment_list;
    free_safe(ns);
    return ret;
}


Namespace *namespace_init(
    char *name,
    char *wal_path,
    char **segment_paths,
    long n_segments
) {
    Namespace *ns = (Namespace *) malloc_safe(sizeof(Namespace));
    int len = strlen(name);
    ns->name = malloc_safe(len + 1);
    strcpy(ns->name, name);
    ns->name[len] = '\0';
    ns->wal_path = wal_path;
    FILE *wal_fp = fopen(wal_path, "a");
    ns->wal_fp = wal_fp;
    unsigned long wal_size = ftell(wal_fp);
    if (wal_size > 0) {
        debug("restoring WAL: %s", wal_path);
        freopen(wal_path, "r+", wal_fp);
        ns->memtab = restore_wal(wal_fp, wal_size);
        debug("finished restoring WAL: %s", wal_path);
        freopen(wal_path, "a", wal_fp);
    }
    else {
        ns->memtab = tree_create();
    }
    write_wal_header(ns->wal_fp);
    ns->segment_list = list_create();
    ns->segment_set = hs_init();
    SSTSegment *seg;
    /* Remember to organize SST segments by age (more recent before least
     * recent). */
    for (long i = 0; i < n_segments; i++) {
        debug("reading SST segment #%ld: %s", i, segment_paths[i]);
        seg = sstsegment_create(segment_paths[i], true);
        list_append(ns->segment_list, seg);
        hs_add(ns->segment_set, segment_paths[i]);
    }
    return ns;
}


void namespace_insert(char cmd, char *key, void *value, size_t value_size, Namespace *ns) {
    debug("inserting key '%s' in namespace '%s'", key, ns->name);
    write_wal_command(cmd, key, value, value_size, ns->wal_fp);
    debug("wrote command '%d' to WAL", cmd);
    tree_insert(ns->memtab, key, value, value_size);
    debug("inserted key '%s' in memtab", key);
}


void namespace_delete(char cmd, char *key, Namespace *ns) {
    debug("deleting key '%s' from namespace '%s'", key, ns->name);
    write_wal_command(cmd, key, NULL, 0, ns->wal_fp);
    debug("wrote command '%d' to WAL", cmd);
    tree_delete(ns->memtab, key);
    debug("deleted key '%s' from memtab", key);
}


/* Searches a key in a namespace (memtables, then SST segments) and returns a
 * new TreeNode object containing the corresponding value. If the key is not
 * found, returns NULL. */
TreeNode *namespace_search(char *key, Namespace *ns) {
    TreeNode *found = tree_search(key, ns->memtab);
    if (found != NULL) {
        debug("key '%s' found in memtable", key);
        return tnode_create(found->key, found->value, found->value_size);
    }
    debug("key '%s' not found in memtable, searching SST segments", key);
    TreeNode *result = NULL;
    long start;
    long end;
    ListNode *node = ns->segment_list->head;
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
