#include <string.h>

#include "debug.h"
#include "io.h"
#include "wal.h"


static const char *VERSION = _VERSION;


/* Reads a Write-Ahead Log into an RB tree, i.e. restores memtable from WAL. */
RBTree *restore_wal(FILE *fp, unsigned long file_size) {
    unsigned long wal_data_size = file_size - VER_SZ;
    debug("wal data size: %ld bytes", wal_data_size);
    void *wal_data = malloc_safe(wal_data_size);
    long record_size = 0;
    char command = 0;
    char key_size = 0;
    char *key = NULL;
    long value_size = 0;
    void *value = NULL;
    unsigned long off = 0;
    RBTree *memtab = tree_create();
    fseek(fp, VER_SZ, SEEK_SET);
    fread(wal_data, wal_data_size, 1, fp);
    while (off < wal_data_size) {
        memcpy(&record_size, wal_data + off, RECORD_LEN_SZ);
        debug("record size: %ld", record_size);
        off += RECORD_LEN_SZ;
        memcpy(&command, wal_data + off, WAL_CMD_SZ);
        debug("command: %d", command);
        off += WAL_CMD_SZ;
        memcpy(&key_size, wal_data + off, KEY_LEN_SZ);
        debug("key size: %d", key_size);
        off += KEY_LEN_SZ;
        key = (char *) malloc_safe(key_size + 1);
        memcpy(key, wal_data + off, key_size);
        debug("key: %s", key);
        off += key_size;
        key[(int)key_size] = '\0';
        value_size = record_size - RECORD_LEN_SZ - WAL_CMD_SZ - KEY_LEN_SZ - key_size;
        debug("value size: %ld", value_size);
        value = malloc_safe(value_size);
        memcpy(value, wal_data + off, value_size);
        off += value_size;
        switch (command) {
            case INSERT:
                tree_insert(memtab, key, value, value_size);
                break;
            case DELETE:
                tree_delete(memtab, key);
                break;
            case CREATE_NS:
                tree_insert(memtab, key, NULL, 0);
                break;
            default:
                debug("unrecognized WAL command: %d", command);
                exit(1);
        }
        free(key);
        free(value);
    }
    free(wal_data);
    return memtab;
}



/* Truncate a WAL and returns a new file pointer to it. */
FILE *truncate_wal(char *path, FILE *fp) {
    debug("truncating WAL: %s", path);
    fseek(fp, 0, SEEK_END);
    debug("WAL %s has len %ld", path, ftell(fp));
    FILE *ret = freopen(path, "w", fp);
    if (!ret) {
        log_warn("failed to truncated WAL %s", path);
    }
    return ret;
}


void write_wal_command(
    char command,
    char *key,
    void *value,
    long value_size,
    FILE *fp
) {
    char key_size = strlen(key);
    long total_size = RECORD_LEN_SZ + WAL_CMD_SZ + KEY_LEN_SZ + key_size + value_size;
    fseek(fp, 0, SEEK_END);
    fwrite(&total_size, RECORD_LEN_SZ, 1, fp);
    fwrite(&command, WAL_CMD_SZ, 1, fp);
    fwrite(&key_size, KEY_LEN_SZ, 1, fp);
    fwrite(key, key_size, 1, fp);
    if (value_size > 0) {
        fwrite(value, value_size, 1, fp);
    }
}


void write_wal_header(FILE *fp) {
    /* version number */
    fwrite(VERSION, VER_SZ, 1, fp);
}
