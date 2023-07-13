#include <stdlib.h>
#include <string.h>

#include "alloc.h"
#include "debug.h"
#include "io.h"
#include "namespace.h"
#include "tree.h"

#define RANDOM_STR_LEN 20


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


/* Writes the memtable to disk, truncates the WAL, and writes the path of the
 * new SST segment in the appropriate segment list of the Db object.
 * We return the segment set so that the caller can take steps to save the
 * segment paths:
 * - user SST segment paths are written to master SST
 * - master SST segment paths are written to root file
 *
 * The return value must be freed by caller.
 */
HashSet *namespace_destroy(Namespace *ns) {
    debug("destroying namespace '%s'", ns->name);
    if (ns->memtab->n > 0) {
        debug("memtab has %ld items", ns->memtab->n);
        char *segment_path = random_string(RANDOM_STR_LEN + 1);
        debug("writing memtable to %s", segment_path);
        write_segment_file(ns->memtab, segment_path);
        debug("adding segment path to segment set");
        hs_add(ns->segment_set, segment_path);
    }
    tree_destroy(ns->memtab);
    freopen(ns->wal_path, "w", ns->wal_fp);
    fclose(ns->wal_fp);
    list_destroy(ns->segment_list);
    HashSet *ret = ns->segment_set;
    free_safe(ns);
    return ret;
}


Namespace *namespace_init(
    char *name,
    char *wal_path,
    char **segment_paths,
    long n_segments
) {
    FILE *wal_fp = fopen(wal_path, "a");
    fseek(wal_fp, 0, SEEK_END);
    if (ftell(wal_fp) > 0) {
        log_err(
            "need to restore WAL for namespace '%s', not implemented yet, exiting\n",
            name
        );
        exit(1);
    }
    Namespace *ns = (Namespace *) malloc_safe(sizeof(Namespace));
    ns->wal_fp = wal_fp;
    write_wal_header(ns->wal_fp);
    int len = strlen(name);
    ns->name = malloc_safe(len + 1);
    strcpy(ns->name, name);
    ns->name[len] = '\0';
    ns->memtab = tree_create();
    ns->segment_list = list_create();
    ns->segment_set = hs_init();
    SSTSegment *seg;
    for (long i = 0; i < n_segments; i++) {
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


TreeNode *namespace_search(char *key, Namespace *ns) {
    TreeNode *result;
    result = tree_search(key, ns->memtab);
    if (result == NULL) {
        long start;
        long end;
        ListNode *node = ns->segment_list->head;
        while (node != NULL) {
            SSTSegment *segment = (SSTSegment *) node->data;
            index_search(key, segment->index, &start, &end);
            if (start != -1) {
                FILE *fp = fopen(segment->path, "r");
                void *data = read_sst_block(fp, start, end);
                result = sst_block_search(key, data, end - start);
                break;
            }
        }
    }
    return result;
}
