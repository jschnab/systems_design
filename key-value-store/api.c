#include "api.h"
#include "debug.h"


static const char *VERSION = _VERSION;


void create_namespace(char *name, Db *db) {
    namespace_insert(CREATE_NS, name, NULL, 0, db->master_ns);
}


void db_close(Db *db) {
    HashSet *segments = NULL;
    char path_len;
    if (db->user_ns != NULL) {
        segments = namespace_destroy(db->user_ns);
        debug("namespace '%s' has %d segments", db->user_ns->name, segments->count);
        if (segments->count > 0) {
            debug("writing segments to master SST memtable");
            /* The key is the namespace name, and the value the list of SST segment
             * paths. First the number of path is stored in 8 bytes, then for each
             * path we store its length in 1 byte, then the path string. */
            /* First we get the total value size. */
            long value_size = SEG_NUM_SZ;
            for (long i = 0; i < segments->size; i++) {
                if (segments->items[i] != NULL && segments->items[i] != HS_DELETED_ITEM) {
                    value_size += strlen(segments->items[i]) + SEG_PATH_LEN_SZ;
                }
            }
            /* Now we can copy segment paths to the value. */
            void *value = malloc_safe(value_size);
            memcpy(value, &segments->count, SEG_NUM_SZ);
            long off = SEG_NUM_SZ;
            for (long i = 0; i < segments->size; i++) {
                if (segments->items[i] != NULL && segments->items[i] != HS_DELETED_ITEM) {
                    path_len = strlen(segments->items[i]);
                    memcpy(value + off, &path_len, SEG_PATH_LEN_SZ);
                    off += SEG_PATH_LEN_SZ;
                    memcpy(value + off, segments->items[i], path_len);
                    off += path_len;
                }
            }
            /* Insert the user namespace paths in the master memtable. */
            namespace_insert(
                ADD_SST_SEG,
                db->user_ns->name,
                value,
                value_size,
                db->master_ns
            );
        }
        hs_destroy(segments);
    }

    segments = namespace_destroy(db->master_ns);
    debug("master table has %d segments", segments->count);
    debug("segments set has %d items", segments->size);
    fseek(db->fp, SEG_NUM_OFF, SEEK_SET);
    fwrite(&segments->count, SEG_NUM_SZ, 1, db->fp);
    if (segments->count > 0) {
        debug("writing segments to root file");
        for (long i = 0; i < segments->size; i++) {
            if (segments->items[i] != NULL && segments->items[i] != HS_DELETED_ITEM) {
                debug("writing master SST segment path %s", segments->items[i]);
                path_len = strlen(segments->items[i]);
                fwrite(&path_len, SEG_PATH_LEN_SZ, 1, db->fp);
                fwrite(segments->items[i], path_len, 1, db->fp);
            }
        }
    }
    hs_destroy(segments);
    fclose(db->fp);
    free_safe(db);
}


Db *db_open(char *path) {
    FILE *fp;
    long n_segments = 0;
    char **segments = NULL;

    if ((fp = fopen(path, "r")) == NULL) {
        debug("database file '%s' does not exist, creating", path);
        fp = fopen(path, "w+");
        fwrite(VERSION, VER_SZ, 1, fp);
    }
    else {
        char len;
        fseek(fp, SEG_NUM_OFF, SEEK_SET);
        fread(&n_segments, SEG_NUM_SZ, 1, fp);
        debug("reading %ld master SST segments", n_segments);
        for (long i = 0; i < n_segments; i++) {
            fread(&len, SEG_PATH_LEN_SZ, 1, fp);
            segments[i] = malloc_safe(len + 1);
            fread(segments[i], len, 1, fp);
            debug("segment %ld path: %s", i, segments[i]);
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
