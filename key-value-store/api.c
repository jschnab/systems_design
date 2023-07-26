#include "api.h"
#include "debug.h"
#include "tree.h"


static const char *VERSION = _VERSION;


void use(char *name, Db *db) {
    if (db->user_tb) {
        user_table_close(db->user_tb, db->master_tb, db->fp);
        db->user_tb = NULL;
    }
    long n_segments = 0;
    char **segments = NULL;
    TreeNode *found = table_get(name, db->master_tb);
    if (found == NULL) {
        debug("user table '%s' not found, creating", name);
        table_put(name, NULL, 0, db->master_tb, NULL, db->fp);
        debug("finished creating user table '%s'", name);

    }
    else if (found->value != NULL) {
        debug("user table '%s' exists", name);
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
        tnode_destroy(found);
    }
    debug("initializing table '%s'", name);
    db->user_tb = table_init(name, segments, n_segments);
    debug("finished initialization for table '%s'", name);
}


void close(Db *db) {
    debug("closing db %s", db->path);
    if (db->user_tb != NULL) {
        user_table_close(db->user_tb, db->master_tb, db->fp);
        db->user_tb = NULL;
    }
    table_compact(db->master_tb);
    memtable_save(db->master_tb);
    master_table_segments_to_root(db->master_tb, db->fp);
    table_destroy(db->master_tb);
    fclose(db->fp);
    free_safe(db);
    log_info("closed db");
}


void db_delete(char *key, Db *db) {
    if (db->user_tb == NULL) {
        log_warn("no active user table, aborting");
        return;
    }
    table_delete(DELETE, key, db->user_tb);
}


/* This function should return a record object, TreeNode is too low level. */
TreeNode *get(char *key, Db *db) {
    if (db->user_tb == NULL) {
        log_warn("no active user table, aborting");
        return NULL;
    }
    return table_get(key, db->user_tb);
}


void put(char *key, void *value, long value_size, Db *db) {
    if (db->user_tb == NULL) {
        log_warn("no active user table, aborting");
        return;
    }
    table_put(key, value, value_size, db->user_tb, db->master_tb, NULL);
}


Db *connect(char *path) {
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

    Table *master = table_init(MASTER_TB_NAME, segments, n_segments);

    Db *db = (Db *) malloc_safe(sizeof(Db));
    db->path = path;
    db->fp = fp;
    db->user_tb = NULL;
    db->master_tb = master;

    return db;
}
