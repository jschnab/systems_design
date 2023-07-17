#include "api.h"
#include "debug.h"
#include "tree.h"


static const char *VERSION = _VERSION;


void namespace_create(char *name, Db *db) {
    if (namespace_search(name, db->master_ns) != NULL) {
        log_info("namespace already exists, won't be created");
        return;
    }
    log_info("inserting namespace '%s' in master table", name);
    namespace_insert(CREATE_NS, name, NULL, 0, db->master_ns);
}


void namespace_use(char *name, Db *db) {
    long n_segments = 0;
    char **segments = NULL;
    TreeNode *found = namespace_search(name, db->master_ns);
    if (found == NULL) {
        log_info("user namespace not found: %s", name);
        return;
    }
    /* If there are SST segments for this namespace. */
    debug("user namespace exists: %s", name);
    if (found->value != NULL) {
        memcpy(&n_segments, found->value, SEG_NUM_SZ);
        debug("number of segments: %ld", n_segments);
        segments = calloc_safe(n_segments, sizeof(char *));
        long off = SEG_NUM_SZ;
        char len;
        for (long i = 0; i < n_segments; i++) {
            memcpy(&len, found->value + off, SEG_PATH_LEN_SZ);
            debug("segment #%ld len: %d", i, len);
            off += SEG_PATH_LEN_SZ;
            segments[i] = malloc_safe(len + 1);
            memcpy(segments[i], found->value + off, len);
            segments[i][(int)len] = '\0';
            debug("segment #%ld path: %s", i, segments[i]);
            off += len;
        }
    }
    tnode_destroy(found);
    /* namespace name +4 for .wal and + 1 for null termination. */
    int len = strlen(name);
    char *wal_path = malloc_safe(len + 5);
    strcpy(wal_path, name);
    strcpy(wal_path + len, ".wal");
    wal_path[len + 4] = '\0';
    debug("initializing namespace object '%s'", name);
    db->user_ns = namespace_init(
        name,
        wal_path,
        segments,
        n_segments
    );
    debug("finished initialization for namespace '%s'", name);
}


void db_close(Db *db) {
    debug("closing db %s", db->path);
    List *segments = NULL;
    char path_len;
    SSTSegment *seg;
    if (db->user_ns != NULL) {
        /* Copy user namespace name for later use, when adding segments paths
         * to master table. */
        char *user_ns_name = malloc_safe(strlen(db->user_ns->name) + 1);
        strcpy(user_ns_name, db->user_ns->name);
        segments = namespace_destroy(db->user_ns);
        debug("user namespace has %ld segments", segments->n);
        if (segments->n > 0) {
            debug("writing segments to master SST memtable");
            /* The key is the namespace name, and the value the list of SST segment
             * paths. First the number of paths is stored in 8 bytes, then for each
             * path we store its length in 1 byte, then the path string. */
            /* First we get the total value size. */
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
                seg = (SSTSegment *)node->data;
                path_len = strlen(seg->path);
                debug("segment %s has length %d", seg->path, path_len);
                memcpy(value + off, &path_len, SEG_PATH_LEN_SZ);
                off += SEG_PATH_LEN_SZ;
                memcpy(value + off, seg->path, path_len);
                off += path_len;
            }
            /* Insert the user namespace paths in the master memtable. */
            namespace_insert(
                ADD_SST_SEG,
                user_ns_name,
                value,
                value_size,
                db->master_ns
            );
            free_safe(user_ns_name);
        }
        list_destroy(segments);
    }

    segments = namespace_destroy(db->master_ns);
    debug("master namespace has %ld segments", segments->n);
    fseek(db->fp, SEG_NUM_OFF, SEEK_SET);
    fwrite(&segments->n, SEG_NUM_SZ, 1, db->fp);
    if (segments->n > 0) {
        debug("writing segments to root file");
        for (ListNode *node = segments->head; node != NULL; node = node->next) {
            seg = (SSTSegment *)node->data;
            debug("writing master SST segment path %s", seg->path);
            path_len = strlen(seg->path);
            fwrite(&path_len, SEG_PATH_LEN_SZ, 1, db->fp);
            fwrite(seg->path, path_len, 1, db->fp);
        }
    }
    list_destroy(segments);
    fclose(db->fp);
    free_safe(db);
    log_info("closed db");
}


TreeNode *db_get(char *key, Db *db) {
    if (db->user_ns == NULL) {
        log_warn("no active user namespace, aborting");
        return NULL;
    }
    return namespace_search(key, db->user_ns);
}


void db_insert(char *key, void *value, long value_size, Db *db) {
    if (db->user_ns == NULL) {
        log_warn("no active user namespace, aborting");
        return;
    }
    namespace_insert(INSERT, key, value, value_size, db->user_ns);
}


Db *db_open(char *path) {
    debug("opening database %s", path);
    FILE *fp;
    long n_segments = 0;
    char **segments = NULL;

    if ((fp = fopen(path, "r")) == NULL) {
        debug("database file '%s' does not exist, creating", path);
        fp = fopen(path, "w+");
        fwrite(VERSION, VER_SZ, 1, fp);
    }
    else {
        fp = fopen(path, "r+");
        char len;
        fseek(fp, SEG_NUM_OFF, SEEK_SET);
        fread(&n_segments, SEG_NUM_SZ, 1, fp);
        debug("found %ld master SST segment(s)", n_segments);
        segments = calloc_safe(n_segments, sizeof(char *));
        for (long i = 0; i < n_segments; i++) {
            fread(&len, SEG_PATH_LEN_SZ, 1, fp);
            debug("segment #%ld has length %d", i, len);
            segments[i] = malloc_safe(len + 1);
            fread(segments[i], len, 1, fp);
            debug("segment #%ld path: %s", i, segments[i]);
        }
    }

    Namespace *master = namespace_init(
        MASTER_NS_NAME,
        MASTER_WAL_PATH,
        segments,
        n_segments
    );

    Db *db = (Db *) malloc_safe(sizeof(Db));
    db->path = path;
    db->fp = fp;
    db->user_ns = NULL;
    db->master_ns = master;

    return db;
}
