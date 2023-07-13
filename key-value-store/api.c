#include "api.h"
#include "debug.h"


static const char *VERSION = _VERSION;


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
